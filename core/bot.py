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
import json
import os
import requests
from core.browser.manager import BrowserManager



from core.database import Database
from core.logger import LogManager


# Maximum continuous run time in seconds (7 hours)
MAX_RUN_SECONDS = 7 * 60 * 60

# Pause between full subreddit sweeps (10 minutes)
SWEEP_INTERVAL = 10 * 60

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
        search_queries = [s.strip() for s in settings.get("search_queries", "").split(",") if s.strip()]
        if not search_queries:
            self._log.log("❌ No search queries configured. Please add them.")
            return

        tools = self._db.get_all_tools()
        if not tools:
            self._log.log("❌ No affiliate tools found. Add some in the Tools Manager.")
            return

        # ---- Init Groq AI Config ----
        try:
            from groq import Groq
            groq_key = settings.get("groq_api_key", "").strip()
            if not groq_key:
                self._log.log("⚠️  Running in Pure Local Mode (No Groq API Key found in settings)")
                groq_client = None
            else:
                groq_client = Groq(api_key=groq_key)
                self._log.log("✅ Groq AI (Llama 3) configured")
        except ImportError:
            self._log.log("⚠️  Running in Pure Local Mode (groq package not installed)")
            groq_client = None

        # ---- Telegram setup (optional) ----
        tg_token = settings.get("telegram_bot_token", "")
        tg_chat_id = settings.get("telegram_chat_id", "")
        telegram_enabled = bool(tg_token and tg_chat_id)
        if telegram_enabled:
            self._log.log("✅ Telegram notifications enabled")
        else:
            self._log.log("⚠️  Telegram not configured — skipping notifications")

        self._log.log(f"📋 Monitoring {len(search_queries)} global search queries: {', '.join(search_queries)}")
        self._log.log(f"🛠️  {len(tools)} tool(s) loaded")
        self._log.log("—" * 50)

        # ---- Main sweep loop ----
        headless = settings.get("headless_mode", "No").strip().lower() == "yes"
        try:
            browser = BrowserManager()
            self._log.log("🌐 Connecting to Automation Chrome Profile...")
            browser.start(headless=headless)
            
            # --- Cookie Injection Logic ---
            cookies_path = "cookies.json"
            if os.path.exists(cookies_path):
                self._log.log("🍪 Found cookies.json! Injecting Reddit session...")
                try:
                    with open(cookies_path, "r", encoding="utf-8") as f:
                        cookies = json.load(f)
                    # We must be on reddit.com to set reddit.com cookies securely
                    browser.goto("https://www.reddit.com")
                    browser.inject_cookies(cookies, "reddit.com")
                    
                    # Rename the file so we don't inject it every single time we start the bot
                    os.rename(cookies_path, "cookies_injected.json")
                    self._log.log("✅ Cookies injected successfully. Renamed file to cookies_injected.json")
                except Exception as e:
                    self._log.log(f"⚠️ Failed to inject cookies: {e}")
            
            # --- Removed requests session extraction ---
            # We keep the browser OPEN because Reddit blocks python requests with 403 Forbidden.
            self._log.log("✅ Using Chrome tabs for scraping to avoid Reddit 403 blocks.")
            
            while not self._stop_event.is_set():
                # 7-hour guard
                elapsed = time.time() - start_time
                if elapsed >= MAX_RUN_SECONDS:
                    self._log.log("⏰ Daily 7-hour limit reached to protect account.")
                    break

                try:
                    self._sweep(browser, groq_client, search_queries, tools, tg_token, tg_chat_id, telegram_enabled)
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

            browser.quit()
        except Exception as e:
            self._log.log(f"❌ Browser automation failed: {e}")

        self._log.log("🛑 Bot stopped.")

    # ------------------------------------------------------------------
    # Internal: single sweep of all subreddits
    # ------------------------------------------------------------------

    def _sweep(
        self, browser, groq_client,
        search_queries: list, tools: list,
        tg_token: str, tg_chat_id: str, telegram_enabled: bool
    ):
        """Perform one pass over all search queries."""
        now_utc = datetime.now(timezone.utc)
        
        for query in search_queries:
            if self._stop_event.is_set():
                return

            # Quick delay between searches
            if self._stop_event.wait(timeout=2):
                return

            self._log.log(f"🔍 Global Search via Chrome: \"{query}\"")
            try:
                import urllib.parse
                safe_query = urllib.parse.quote(query)
                url = f"https://www.reddit.com/search/?q={safe_query}&sort=new"
                
                browser.open_tab(url)
                # Wait 5 seconds to act human-like and let the UI render fully
                time.sleep(5)
                # Scroll down slightly to trigger lazy loading if needed
                browser.driver.execute_script("window.scrollTo(0, 1500);")
                time.sleep(2)
                
                js_script = """
                let results = [];
                let posts = document.querySelectorAll('shreddit-post');
                for (let p of posts) {
                    try {
                        let id = p.getAttribute('id');
                        let title = p.getAttribute('post-title') || '';
                        let permalink = p.getAttribute('permalink') || '';
                        let created_ts = p.getAttribute('created-timestamp');
                        let created_utc = created_ts ? (new Date(created_ts).getTime() / 1000) : null;
                        
                        let body_el = p.querySelector('[slot="text-body"]');
                        let body = body_el ? body_el.innerText : '';
                        
                        results.push({
                            id: id, 
                            title: title, 
                            selftext: body, 
                            permalink: permalink, 
                            created_utc: created_utc
                        });
                    } catch(e) {}
                }
                return results;
                """
                
                posts = browser.driver.execute_script(js_script)
                browser.close_tab()
                
            except Exception as e:
                self._log.log(f"   ⚠️  Could not fetch r/{sub_name}: {e}")
                try: browser.close_tab() 
                except: pass
                continue

            for post_item in posts:
                if self._stop_event.is_set():
                    return

                post_id = post_item.get('id')

                if not post_id:
                    continue

                # Skip already processed
                if self._db.is_post_processed(post_id):
                    continue

                # Skip posts older than 3 hours
                post_utc = post_item.get('created_utc')
                if post_utc:
                    post_time = datetime.fromtimestamp(post_utc, tz=timezone.utc)
                    age_seconds = (now_utc - post_time).total_seconds()
                    if age_seconds > MAX_POST_AGE:
                        continue

                title = post_item.get('title', '')
                post_body = post_item.get('selftext', '')[:2000]  # Truncate very long posts
                permalink = post_item.get('permalink', '')
                
                # --- Advanced "Lead Scoring" Filter ---
                combined_text = (title + " " + post_body).lower()
                
                # 1. Self-Promotion Blocker (Reject instantly)
                self_promo_phrases = ["i built", "my new app", "check out my", "i made", "day 1 to", "my traffic exchange", "i created"]
                if any(p in combined_text for p in self_promo_phrases):
                    self._log.log(f"   ⏭️  Skipped (Self Promotion Detected): \"{title[:50]}\"")
                    self._db.mark_post_processed(post_id)
                    continue
                    
                # 2. Buying Intent Match
                intent_phrases = ["looking for", "need help finding", "is there a", "recommendations", "how can i", "alternative", "any advice", "struggling with", "how do i"]
                has_intent = any(p in combined_text for p in intent_phrases)
                
                # 3. Context Match
                context_words = ["tool", "software", "app", "platform", "solution", "website", "way to"]
                has_context = any(p in combined_text for p in context_words)
                
                # Logic: Must have both intent AND context, unless it's a very strong direct question
                is_lead = (has_intent and has_context) or ("is there an app" in combined_text)
                
                if not is_lead:
                    self._log.log(f"   ⏭️  Skipped (No Buying Intent): \"{title[:50]}\"")
                    # Mark processed so we don't scan it again
                    self._db.mark_post_processed(post_id)
                    continue

                self._log.log(f"   🎯 Target Lead Found: \"{title[:80]}\"")

                # Generate a smart Local Template (No-AI)
                # --- Generate Reply ---
                if not groq_client:
                    # Fallback to local routing
                    suggested_tool = "my tool"
                    if tools:
                        if any(kw in combined_text for kw in ["social", "post", "schedule", "instagram", "content", "marketing", "facebook"]):
                            for t in tools:
                                if "Ocoya" in t["name"]:
                                    suggested_tool = "Ocoya"
                                    break
                        elif any(kw in combined_text for kw in ["chat", "bot", "support", "document", "knowledge", "customer"]):
                            for t in tools:
                                if "CustomGPT" in t["name"]:
                                    suggested_tool = "CustomGPT"
                                    break
                        else:
                            for t in tools:
                                if "CustomGPT" in t["name"]:
                                    suggested_tool = "CustomGPT"
                                    break
                    import random
                    clean_title = title.lower().strip()
                    if len(clean_title) > 30:
                        clean_title = clean_title[:30] + "..."
                    templates = [
                        f"Man I totally get what you're saying about {clean_title}. I was struggling with the exact same thing a while ago. You might want to look into {suggested_tool}, it pretty much automated that entire headache for me. I dropped the exact name of it on my page if you're curious, but either way good luck with it!",
                        f"Read your post and it really resonated. Dealing with {clean_title} can be super annoying. Have you tried looking into {suggested_tool}? I started using it recently and it saved me so much time. I have a brief write-up about it on my wall if it helps.",
                        f"I've been in the exact same boat. The easiest workaround I found was just using {suggested_tool}. It handles all the heavy lifting. I actually mentioned it on my bio if you want to see which one I use. Hope that helps man."
                    ]
                    reply_text = random.choice(templates)
                else:
                    self._log.log(f"   🤖 Sending to Groq (Llama 3): \"{title[:80]}\"")
                    
                    # Construct tools context
                    tools_desc = ""
                    for t in tools:
                        tools_desc += f"Tool Name: {t['name']}\nDescription: {t['description']}\n\n"
                        
                    system_prompt = (
                        "You are a casual 25-year-old Reddit user browsing forums. You must write a highly authentic, natural-sounding comment recommending a software tool.\n\n"
                        "STRICT RULES TO AVOID REDDIT SPAM FILTERS:\n"
                        "1. Write EXACTLY like a real human. Use lowercase where natural, words like 'tbh', 'man', 'ngl'. DO NOT sound corporate or like an AI.\n"
                        "2. Start by acknowledging the user's specific problem in 1 sentence to prove you read the post.\n"
                        "3. Recommend ONE of the provided tools by name ONLY. DO NOT include any links.\n"
                        "4. NEVER use the words 'pinned post', 'profile', 'affiliate', or 'link'. Instead, casually mention: 'I actually dropped the name of it on my bio if you want to check it out' or 'I have a brief write up on my wall'.\n"
                        "5. Keep it under 4 sentences.\n\n"
                        f"AVAILABLE TOOLS:\n{tools_desc}"
                    )
                    
                    try:
                        chat_completion = groq_client.chat.completions.create(
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": f"Post Title: {title}\n\nPost Body: {post_body}"}
                            ],
                            model="llama-3.1-8b-instant",
                        )
                        reply_text = chat_completion.choices[0].message.content.strip()
                    except Exception as e:
                        self._log.log(f"   ⚠️  Groq API Error: {e}")
                        continue

                # Mark as processed regardless of outcome
                self._db.mark_post_processed(post_id)

                self._log.log("   ✅ Match found! Sending Telegram notification…")

                # Send Telegram notification
                if telegram_enabled:
                    self._send_telegram(
                        tg_token, tg_chat_id,
                        post_title=title,
                        post_url=f"https://www.reddit.com{permalink}",
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
            f"🔔 New Affiliate Opportunity\n\n"
            f"Post: {post_title}\n"
            f"URL: {post_url}\n\n"
            f"Drafted Comment:\n{comment}"
        )
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
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
