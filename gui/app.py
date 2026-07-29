"""
app.py — Main Application Window

Creates the CustomTkinter root window with a tabbed interface
(Dashboard, Tools Manager, Settings) and wires up all components.
"""

import customtkinter as ctk

from core.database import Database
from core.logger import LogManager
from core.bot import BotEngine
from gui.dashboard import DashboardTab
from gui.tools_manager import ToolsManagerTab
from gui.settings import SettingsTab


# Color palette (global window level)
COLOR_BG_DARK = "#0f0f0f"
COLOR_TAB_BG = "#141425"
COLOR_TAB_SELECTED = "#6c63ff"
COLOR_TAB_HOVER = "#1e1e3a"
COLOR_TEXT = "#e0e0e0"


class App(ctk.CTk):
    """Root window for the AI Affiliate Marketing Bot."""

    def __init__(self):
        super().__init__()

        # ---- Window config ----
        self.title("DZ-GHOST · AI Affiliate Marketing Bot")
        self.geometry("1100x720")
        self.minsize(900, 600)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.configure(fg_color=COLOR_BG_DARK)

        # ---- Core components ----
        self.db = Database()
        self.log_manager = LogManager()
        self.bot_engine = BotEngine(self.db, self.log_manager)

        # ---- Build UI ----
        self._build_tabview()

    def _build_tabview(self):
        """Create the 3-tab interface."""
        self._tabview = ctk.CTkTabview(
            self,
            fg_color=COLOR_TAB_BG,
            segmented_button_fg_color="#1a1a2e",
            segmented_button_selected_color=COLOR_TAB_SELECTED,
            segmented_button_selected_hover_color="#574fd6",
            segmented_button_unselected_color="#1a1a2e",
            segmented_button_unselected_hover_color=COLOR_TAB_HOVER,
            text_color=COLOR_TEXT,
            corner_radius=16,
            border_width=0,
        )
        self._tabview.pack(fill="both", expand=True, padx=16, pady=16)

        # Create tabs
        tab_dashboard = self._tabview.add("  📊 Dashboard  ")
        tab_tools = self._tabview.add("  🛠️ Tools Manager  ")
        tab_settings = self._tabview.add("  ⚙️ Settings  ")

        # Initialize tab contents
        self.dashboard = DashboardTab(tab_dashboard, self.bot_engine, self.log_manager)
        self.tools_manager = ToolsManagerTab(tab_tools, self.db)
        self.settings = SettingsTab(tab_settings, self.db)

        # Default to dashboard
        self._tabview.set("  📊 Dashboard  ")
