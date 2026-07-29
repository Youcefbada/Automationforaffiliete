"""
bot.py — Background Bot Engine

Implements the core loop:
  1. Load settings + tools from SQLite
  2. Init PRAW (Reddit) and Gemini clients
  3. Sweep subreddits for new posts → ask Gemini → notify via Telegram
  4. Auto-stop after 7 hours to protect the Reddit account
  5. Resilient: catches errors, logs, waits 60s, retries
"""

import threading
import time
from datetime import datetime, timezone

import praw
import requests

try:
    from google import genai
except ImportError:
    genai = None

from core.database import Database
from core.logger import LogManager


# Maximum continuous run time in seconds (7 hours)
MAX_RUN_SECONDS = 7 * 60 * 60

# Pause between full subreddit sweeps (5 minutes)
SWEEP_INTERVAL = 5 * 60

# Pause between Gemini API calls (free-tier rate limit)
GEMINI_CALL_DELAY = 15

# Maximum post age in seconds (3 hours)
MAX_POST_AGE = 3 * 60 * 60


class BotEngine:
    """Runs the affiliate marketing bot in a background daemon thread."""

    def __init__(self, database: Database, log_manager: LogManager):
        self._db = database
        self._log = log_manager
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    # ------------------------------------------------------------------
    # Public API (called from GUI thread)
    # ------------------------------------------------------------------

    def start(self):
        """Launch the bot in a background thread."""
        if self.is_running():
            self._log.log("Bot is already running.")
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        """Signal the bot to stop gracefully."""
        self._stop_event.set()
        self._log.log("Stop signal sent — bot will halt after current cycle.")

    def is_running(self) -> bool:
        """Check if the bot thread is alive."""
        return self._thread is not None and self._thread.is_alive()

    # ------------------------------------------------------------------
    # Internal: main loop
    # ------------------------------------------------------------------

    def _run(self):
        """Entry point for the background thread."""
        self._log.log("🚀 Bot starting up…")
        start_time = time.time()

        # ---- Load settings ----
        settings = self._db.get_all_settings()
        required_keys = [
            "reddit_client_id", "reddit_client_secret",
            "reddit_username", "reddit_password", "reddit_user_agent",
            "gemini_api_key", "subreddits",
        ]
        missing = [k for k in required_keys if not settings.get(k)]
        if missing:
            self._log.log(f"❌ Missing settings: {', '.join(missing)}")
            self._log.log("Please fill in the Settings tab and try again.")
            return

        subreddits = [s.strip() for s in settings["subreddits"].split(",") if s.strip()]
        if not subreddits:
            self._log.log("❌ No subreddits configured.")
            return

        tools = self._db.get_all_tools()
        if not tools:
            self._log.log("❌ No affiliate tools found. Add some in the Tools Manager.")
            return

        # ---- Init Reddit (PRAW) ----
        try:
            reddit = praw.Reddit(
                client_id=settings["reddit_client_id"],
                client_secret=settings["reddit_client_secret"],
                username=settings["reddit_username"],
                password=settings["reddit_password"],
                user_agent=settings["reddit_user_agent"],
            )
            # Quick validation
            reddit.user.me()
            self._log.log(f"✅ Reddit authenticated as u/{settings['reddit_username']}")
        except Exception as e:
            self._log.log(f"❌ Reddit auth failed: {e}")
            return

        # ---- Init Gemini ----
        if genai is None:
            self._log.log("❌ google-genai package not installed.")
            return
        try:
            gemini_client = genai.Client(api_key=settings["gemini_api_key"])
            model_name = "gemini-2.0-flash"
            self._log.log(f"✅ Gemini AI configured ({model_name})")
        except Exception as e:
            self._log.log(f"❌ Gemini init failed: {e}")
            return

        # ---- Telegram setup (optional) ----
        tg_token = settings.get("telegram_bot_token", "")
        tg_chat_id = settings.get("telegram_chat_id", "")
        telegram_enabled = bool(tg_token and tg_chat_id)
        if telegram_enabled:
            self._log.log("✅ Telegram notifications enabled")
        else:
            self._log.log("⚠️  Telegram not configured — skipping notifications")

        self._log.log(f"📋 Monitoring {len(subreddits)} subreddit(s): {', '.join(subreddits)}")
        self._log.log(f"🛠️  {len(tools)} tool(s) loaded")
        self._log.log("—" * 50)

        # ---- Main sweep loop ----
        while not self._stop_event.is_set():
            # 7-hour guard
            elapsed = time.time() - start_time
            if elapsed >= MAX_RUN_SECONDS:
                self._log.log("⏰ Daily 7-hour limit reached to protect account.")
                break

            try:
                self._sweep(reddit, gemini_client, model_name, subreddits, tools, tg_token, tg_chat_id, telegram_enabled)
            except Exception as e:
                self._log.log(f"⚠️  Error during sweep: {e}")
                self._log.log("Retrying in 60 seconds…")
                # Wait 60s but remain responsive to stop signal
                if self._stop_event.wait(timeout=60):
                    break
                continue

            # Wait between sweeps, but remain responsive to stop signal
            remaining_hours = max(0, (MAX_RUN_SECONDS - (time.time() - start_time)) / 3600)
            self._log.log(f"💤 Sweep complete. Sleeping {SWEEP_INTERVAL // 60} min "
                          f"({remaining_hours:.1f}h remaining in shift)…")
            self._log.log("—" * 50)
            if self._stop_event.wait(timeout=SWEEP_INTERVAL):
                break

        self._log.log("🛑 Bot stopped.")

    # ------------------------------------------------------------------
    # Internal: single sweep of all subreddits
    # ------------------------------------------------------------------

    def _sweep(self, reddit, gemini_client, model_name, subreddits, tools, tg_token, tg_chat_id, telegram_enabled):
        """Iterate over each subreddit, fetch posts, analyse with Gemini."""
        tools_description = "\n".join(
            f"- {t['name']}: {t['description']} (Link: {t['affiliate_link']})"
            for t in tools
        )
        now_utc = datetime.now(timezone.utc)

        for sub_name in subreddits:
            if self._stop_event.is_set():
                return

            self._log.log(f"🔍 Scanning r/{sub_name}…")
            try:
                subreddit = reddit.subreddit(sub_name)
                posts = list(subreddit.new(limit=10))
            except Exception as e:
                self._log.log(f"   ⚠️  Could not fetch r/{sub_name}: {e}")
                continue

            for post in posts:
                if self._stop_event.is_set():
                    return

                # Skip already processed
                if self._db.is_post_processed(post.id):
                    continue

                # Skip posts older than 3 hours
                post_time = datetime.fromtimestamp(post.created_utc, tz=timezone.utc)
                age_seconds = (now_utc - post_time).total_seconds()
                if age_seconds > MAX_POST_AGE:
                    continue

                self._log.log(f"   📝 Analysing: \"{post.title[:80]}\"")

                # Build the Gemini prompt
                post_body = (post.selftext or "")[:2000]  # Truncate very long posts
                prompt = (
                    f"You are an expert Reddit user. Read this post:\n\n"
                    f"Title: {post.title}\n"
                    f"Text: {post_body}\n\n"
                    f"Here are my AI tools:\n{tools_description}\n\n"
                    f"Does the user need one of these tools? "
                    f"If NO, just reply 'NO'. "
                    f"If YES, pick the best tool and write a helpful, friendly Reddit "
                    f"comment in the language of the post, offering advice first, "
                    f"then recommending the tool with its link."
                )

                # Call Gemini with rate limiting
                try:
                    response = gemini_client.models.generate_content(
                        model=model_name, contents=prompt
                    )
                    reply_text = response.text.strip()
                except Exception as e:
                    self._log.log(f"   ⚠️  Gemini error: {e}")
                    time.sleep(GEMINI_CALL_DELAY)
                    continue

                time.sleep(GEMINI_CALL_DELAY)

                # Mark as processed regardless of outcome
                self._db.mark_post_processed(post.id)

                if reply_text.upper() == "NO":
                    self._log.log("   ⏭️  Not relevant — skipped.")
                    continue

                self._log.log("   ✅ Match found! Sending Telegram notification…")

                # Send Telegram notification
                if telegram_enabled:
                    self._send_telegram(
                        tg_token, tg_chat_id,
                        post_title=post.title,
                        post_url=f"https://reddit.com{post.permalink}",
                        comment=reply_text,
                    )
                else:
                    self._log.log("   (Telegram disabled — comment logged only)")
                    self._log.log(f"   💬 Drafted comment:\n{reply_text[:300]}")

    # ------------------------------------------------------------------
    # Internal: Telegram notification
    # ------------------------------------------------------------------

    def _send_telegram(self, token: str, chat_id: str, post_title: str, post_url: str, comment: str):
        """Send a message to a Telegram chat via the Bot API."""
        message = (
            f"🔔 *New Affiliate Opportunity*\n\n"
            f"*Post:* {post_title}\n"
            f"*URL:* {post_url}\n\n"
            f"*Drafted Comment:*\n{comment}"
        )
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        }
        try:
            resp = requests.post(url, json=payload, timeout=15)
            if resp.ok:
                self._log.log("   📨 Telegram notification sent!")
            else:
                self._log.log(f"   ⚠️  Telegram error {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            self._log.log(f"   ⚠️  Telegram send failed: {e}")
