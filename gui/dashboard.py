"""
dashboard.py — Dashboard Tab

Live log console, Start/Stop buttons, and bot status indicator.
Polls the LogManager queue every 100ms via tkinter.after().
"""

import customtkinter as ctk

from core.bot import BotEngine
from core.logger import LogManager


# Color palette
COLOR_BG_DARK = "#0f0f0f"
COLOR_CARD = "#1a1a2e"
COLOR_ACCENT = "#6c63ff"
COLOR_ACCENT_HOVER = "#574fd6"
COLOR_GREEN = "#00e676"
COLOR_RED = "#ff5252"
COLOR_TEXT = "#e0e0e0"
COLOR_TEXT_DIM = "#8888aa"
COLOR_BORDER = "#2a2a3e"


class DashboardTab:
    """Builds the Dashboard tab inside a CTkTabview tab."""

    def __init__(self, parent: ctk.CTkFrame, bot_engine: BotEngine, log_manager: LogManager):
        self._parent = parent
        self._bot = bot_engine
        self._log = log_manager

        self._build_ui()
        self._poll_logs()      # Start polling
        self._poll_status()    # Start status polling

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        # ---- Header area ----
        header = ctk.CTkFrame(self._parent, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 10))

        title = ctk.CTkLabel(
            header, text="📊  Dashboard",
            font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"),
            text_color=COLOR_TEXT,
        )
        title.pack(side="left")

        # Status badge
        self._status_frame = ctk.CTkFrame(header, fg_color=COLOR_CARD, corner_radius=20, border_width=1, border_color=COLOR_BORDER)
        self._status_frame.pack(side="right", padx=5)

        self._status_dot = ctk.CTkLabel(
            self._status_frame, text="●", font=ctk.CTkFont(size=14),
            text_color=COLOR_RED, width=20,
        )
        self._status_dot.pack(side="left", padx=(12, 4), pady=8)

        self._status_label = ctk.CTkLabel(
            self._status_frame, text="Bot Status: Stopped",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=COLOR_TEXT_DIM,
        )
        self._status_label.pack(side="left", padx=(0, 14), pady=8)

        # ---- Control buttons ----
        btn_frame = ctk.CTkFrame(self._parent, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(0, 10))

        self._start_btn = ctk.CTkButton(
            btn_frame, text="▶  Start Bot",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            fg_color=COLOR_GREEN, hover_color="#00c853",
            text_color="#0f0f0f", corner_radius=10,
            height=42, width=160,
            command=self._start_bot,
        )
        self._start_btn.pack(side="left", padx=(0, 12))

        self._stop_btn = ctk.CTkButton(
            btn_frame, text="⏹  Stop Bot",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            fg_color=COLOR_RED, hover_color="#d32f2f",
            text_color="#ffffff", corner_radius=10,
            height=42, width=160,
            command=self._stop_bot,
            state="disabled",
        )
        self._stop_btn.pack(side="left")

        # ---- Log console ----
        console_label = ctk.CTkLabel(
            self._parent, text="Live Log Console",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=COLOR_TEXT_DIM, anchor="w",
        )
        console_label.pack(fill="x", padx=22, pady=(5, 2))

        self._console = ctk.CTkTextbox(
            self._parent,
            font=ctk.CTkFont(family="Courier New", size=13),
            fg_color=COLOR_CARD,
            text_color=COLOR_TEXT,
            border_width=1,
            border_color=COLOR_BORDER,
            corner_radius=12,
            wrap="word",
            state="disabled",  # Read-only
        )
        self._console.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        # Welcome message
        self._append_to_console("Welcome to DZ-GHOST AI Affiliate Bot 🤖")
        self._append_to_console("Configure your settings, add tools, then hit Start.")
        self._append_to_console("—" * 55)

    # ------------------------------------------------------------------
    # Bot controls
    # ------------------------------------------------------------------

    def _start_bot(self):
        """Start the bot and toggle button states."""
        self._bot.start()
        self._start_btn.configure(state="disabled")
        self._stop_btn.configure(state="normal")

    def _stop_bot(self):
        """Stop the bot and toggle button states."""
        self._bot.stop()
        self._stop_btn.configure(state="disabled")
        # Start button re-enabled when status polling detects thread death

    # ------------------------------------------------------------------
    # Polling (thread-safe GUI updates via after())
    # ------------------------------------------------------------------

    def _poll_logs(self):
        """Drain the log queue and append messages to the console."""
        messages = self._log.get_messages()
        for msg in messages:
            self._append_to_console(msg)
        # Schedule next poll in 100ms
        self._parent.after(100, self._poll_logs)

    def _poll_status(self):
        """Update the status badge to reflect bot thread state."""
        if self._bot.is_running():
            self._status_dot.configure(text_color=COLOR_GREEN)
            self._status_label.configure(text="Bot Status: Running", text_color=COLOR_GREEN)
        else:
            self._status_dot.configure(text_color=COLOR_RED)
            self._status_label.configure(text="Bot Status: Stopped", text_color=COLOR_TEXT_DIM)
            # Re-enable start button when bot dies
            self._start_btn.configure(state="normal")
            self._stop_btn.configure(state="disabled")
        self._parent.after(500, self._poll_status)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _append_to_console(self, text: str):
        """Insert text into the read-only CTkTextbox."""
        self._console.configure(state="normal")
        self._console.insert("end", text + "\n")
        self._console.see("end")  # Auto-scroll
        self._console.configure(state="disabled")
