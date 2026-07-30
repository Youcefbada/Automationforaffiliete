"""
settings.py — Settings Tab

Input fields for all API keys and configuration.
Saves / loads from the SQLite settings table (key-value store).
"""

import customtkinter as ctk

from core.database import Database


# Color palette
COLOR_CARD = "#1a1a2e"
COLOR_ACCENT = "#6c63ff"
COLOR_ACCENT_HOVER = "#574fd6"
COLOR_GREEN = "#00e676"
COLOR_TEXT = "#e0e0e0"
COLOR_TEXT_DIM = "#8888aa"
COLOR_BORDER = "#2a2a3e"
COLOR_INPUT_BG = "#16162a"


# Settings schema: (db_key, label, placeholder, is_secret)
SETTINGS_SCHEMA = [
    ("section", "Google Gemini", None, None),
    ("gemini_api_key", "API Key", "Your Gemini API key", True),

    ("section", "Telegram Notifications", None, None),
    ("telegram_bot_token", "Bot Token",  "Telegram bot token from @BotFather", True),
    ("telegram_chat_id",   "Chat ID",    "Your Telegram chat ID",              False),

    ("section", "Browser Settings", None, None),
    ("headless_mode", "Headless Mode", "Yes (hidden) or No (visible)", False),

    ("section", "Target Subreddits", None, None),
    ("subreddits", "Subreddits", "Comma separated, e.g. SaaS,startups,freelance", False),
]


class SettingsTab:
    """Builds the Settings tab inside a CTkTabview tab."""

    def __init__(self, parent: ctk.CTkFrame, database: Database):
        self._parent = parent
        self._db = database
        self._entries: dict[str, ctk.CTkEntry] = {}  # db_key → Entry widget

        self._build_ui()
        self._load_settings()

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        # ---- Header ----
        title = ctk.CTkLabel(
            self._parent, text="⚙️  Settings",
            font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"),
            text_color=COLOR_TEXT, anchor="w",
        )
        title.pack(fill="x", padx=20, pady=(20, 5))

        subtitle = ctk.CTkLabel(
            self._parent,
            text="Configure your API keys and preferences. All data is stored locally.",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color=COLOR_TEXT_DIM, anchor="w",
        )
        subtitle.pack(fill="x", padx=22, pady=(0, 15))

        # ---- Scrollable form ----
        scroll = ctk.CTkScrollableFrame(
            self._parent, fg_color="transparent", corner_radius=0,
        )
        scroll.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        current_card = None

        for item in SETTINGS_SCHEMA:
            if item[0] == "section":
                # Section header → new card
                section_name = item[1]
                current_card = ctk.CTkFrame(
                    scroll, fg_color=COLOR_CARD,
                    corner_radius=14, border_width=1, border_color=COLOR_BORDER,
                )
                current_card.pack(fill="x", pady=(0, 14))

                ctk.CTkLabel(
                    current_card, text=section_name,
                    font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
                    text_color=COLOR_ACCENT, anchor="w",
                ).pack(fill="x", padx=16, pady=(14, 6))
                continue

            db_key, label, placeholder, is_secret = item

            field_frame = ctk.CTkFrame(current_card, fg_color="transparent")
            field_frame.pack(fill="x", padx=16, pady=(0, 10))

            ctk.CTkLabel(
                field_frame, text=label,
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=COLOR_TEXT_DIM, anchor="w",
            ).pack(fill="x")

            entry = ctk.CTkEntry(
                field_frame, placeholder_text=placeholder,
                fg_color=COLOR_INPUT_BG, border_color=COLOR_BORDER,
                text_color=COLOR_TEXT, height=38, corner_radius=8,
                show="•" if is_secret else "",
            )
            entry.pack(fill="x", pady=(4, 0))

            # Add bottom padding to last field in card
            self._entries[db_key] = entry

        # Add bottom padding inside each card
        for card in scroll.winfo_children():
            if isinstance(card, ctk.CTkFrame) and card.cget("fg_color") == COLOR_CARD:
                spacer = ctk.CTkFrame(card, fg_color="transparent", height=6)
                spacer.pack()

        # ---- Save button ----
        btn_frame = ctk.CTkFrame(self._parent, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(0, 20))

        self._save_btn = ctk.CTkButton(
            btn_frame, text="💾  Save Settings",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            fg_color=COLOR_ACCENT, hover_color=COLOR_ACCENT_HOVER,
            text_color="#ffffff", corner_radius=10,
            height=44, width=200,
            command=self._save_settings,
        )
        self._save_btn.pack(side="left")

        self._status_label = ctk.CTkLabel(
            btn_frame, text="",
            font=ctk.CTkFont(size=13), text_color=COLOR_GREEN,
        )
        self._status_label.pack(side="left", padx=16)

    # ------------------------------------------------------------------
    # Save / Load
    # ------------------------------------------------------------------

    def _save_settings(self):
        """Persist all field values to the SQLite settings table."""
        for db_key, entry in self._entries.items():
            value = entry.get().strip()
            self._db.save_setting(db_key, value)

        # Show confirmation
        self._status_label.configure(text="✅ Settings saved!")
        self._parent.after(3000, lambda: self._status_label.configure(text=""))

    def _load_settings(self):
        """Pre-fill entry fields from the database."""
        settings = self._db.get_all_settings()
        for db_key, entry in self._entries.items():
            value = settings.get(db_key, "")
            if value:
                entry.delete(0, "end")
                entry.insert(0, value)
