"""
tools_manager.py — Tools Manager Tab

CRUD interface for affiliate tools:
  - Input fields for name, description, affiliate link
  - Add button with validation
  - Scrollable list of tool cards with delete buttons
  - All data persisted in SQLite
"""

import customtkinter as ctk

from core.database import Database


# Color palette (shared with dashboard)
COLOR_CARD = "#1a1a2e"
COLOR_ACCENT = "#6c63ff"
COLOR_ACCENT_HOVER = "#574fd6"
COLOR_GREEN = "#00e676"
COLOR_RED = "#ff5252"
COLOR_TEXT = "#e0e0e0"
COLOR_TEXT_DIM = "#8888aa"
COLOR_BORDER = "#2a2a3e"
COLOR_INPUT_BG = "#16162a"


class ToolsManagerTab:
    """Builds the Tools Manager tab inside a CTkTabview tab."""

    def __init__(self, parent: ctk.CTkFrame, database: Database):
        self._parent = parent
        self._db = database

        self._build_ui()
        self._refresh_tools_list()

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        # ---- Header ----
        title = ctk.CTkLabel(
            self._parent, text="🛠️  Tools Manager",
            font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"),
            text_color=COLOR_TEXT, anchor="w",
        )
        title.pack(fill="x", padx=20, pady=(20, 5))

        subtitle = ctk.CTkLabel(
            self._parent, text="Add your affiliate tools so the bot knows what to recommend.",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color=COLOR_TEXT_DIM, anchor="w",
        )
        subtitle.pack(fill="x", padx=22, pady=(0, 15))

        # ---- Add Tool Form ----
        form_card = ctk.CTkFrame(
            self._parent, fg_color=COLOR_CARD,
            corner_radius=14, border_width=1, border_color=COLOR_BORDER,
        )
        form_card.pack(fill="x", padx=20, pady=(0, 15))

        # Row 1: Name + Link
        row1 = ctk.CTkFrame(form_card, fg_color="transparent")
        row1.pack(fill="x", padx=16, pady=(16, 8))

        # Name
        name_frame = ctk.CTkFrame(row1, fg_color="transparent")
        name_frame.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ctk.CTkLabel(
            name_frame, text="Tool Name", font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLOR_TEXT_DIM, anchor="w",
        ).pack(fill="x")
        self._name_entry = ctk.CTkEntry(
            name_frame, placeholder_text="e.g. ChatGPT Pro",
            fg_color=COLOR_INPUT_BG, border_color=COLOR_BORDER,
            text_color=COLOR_TEXT, height=38, corner_radius=8,
        )
        self._name_entry.pack(fill="x", pady=(4, 0))

        # Link
        link_frame = ctk.CTkFrame(row1, fg_color="transparent")
        link_frame.pack(side="left", fill="x", expand=True, padx=(8, 0))
        ctk.CTkLabel(
            link_frame, text="Affiliate Link", font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLOR_TEXT_DIM, anchor="w",
        ).pack(fill="x")
        self._link_entry = ctk.CTkEntry(
            link_frame, placeholder_text="https://example.com/ref=...",
            fg_color=COLOR_INPUT_BG, border_color=COLOR_BORDER,
            text_color=COLOR_TEXT, height=38, corner_radius=8,
        )
        self._link_entry.pack(fill="x", pady=(4, 0))

        # Row 2: Description (full width)
        desc_frame = ctk.CTkFrame(form_card, fg_color="transparent")
        desc_frame.pack(fill="x", padx=16, pady=(0, 8))
        ctk.CTkLabel(
            desc_frame, text="Description (what it does)",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLOR_TEXT_DIM, anchor="w",
        ).pack(fill="x")
        self._desc_entry = ctk.CTkEntry(
            desc_frame,
            placeholder_text="e.g. AI writing assistant that helps create blog posts and emails",
            fg_color=COLOR_INPUT_BG, border_color=COLOR_BORDER,
            text_color=COLOR_TEXT, height=38, corner_radius=8,
        )
        self._desc_entry.pack(fill="x", pady=(4, 0))

        # Add button
        self._add_btn = ctk.CTkButton(
            form_card, text="＋  Add Tool",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            fg_color=COLOR_ACCENT, hover_color=COLOR_ACCENT_HOVER,
            text_color="#ffffff", corner_radius=10,
            height=42, width=160,
            command=self._add_tool,
        )
        self._add_btn.pack(pady=(4, 16))

        # ---- Tools list header ----
        list_header = ctk.CTkFrame(self._parent, fg_color="transparent")
        list_header.pack(fill="x", padx=22, pady=(5, 5))

        ctk.CTkLabel(
            list_header, text="Your Tools",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color=COLOR_TEXT, anchor="w",
        ).pack(side="left")

        self._count_label = ctk.CTkLabel(
            list_header, text="0 tools",
            font=ctk.CTkFont(size=12), text_color=COLOR_TEXT_DIM, anchor="e",
        )
        self._count_label.pack(side="right")

        # ---- Scrollable tools list ----
        self._scroll_frame = ctk.CTkScrollableFrame(
            self._parent, fg_color="transparent",
            corner_radius=0,
        )
        self._scroll_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

    # ------------------------------------------------------------------
    # CRUD Actions
    # ------------------------------------------------------------------

    def _add_tool(self):
        """Validate inputs, insert into DB, refresh list."""
        name = self._name_entry.get().strip()
        desc = self._desc_entry.get().strip()
        link = self._link_entry.get().strip()

        if not name or not desc or not link:
            # Flash the border of empty fields red briefly
            for entry, value in [(self._name_entry, name), (self._desc_entry, desc), (self._link_entry, link)]:
                if not value:
                    entry.configure(border_color=COLOR_RED)
                    entry.after(1500, lambda e=entry: e.configure(border_color=COLOR_BORDER))
            return

        self._db.add_tool(name, desc, link)

        # Clear inputs
        self._name_entry.delete(0, "end")
        self._desc_entry.delete(0, "end")
        self._link_entry.delete(0, "end")

        self._refresh_tools_list()

    def _delete_tool(self, tool_id: int):
        """Remove a tool from the DB and refresh the list."""
        self._db.delete_tool(tool_id)
        self._refresh_tools_list()

    def _refresh_tools_list(self):
        """Rebuild the scrollable list from DB data."""
        # Clear existing children
        for widget in self._scroll_frame.winfo_children():
            widget.destroy()

        tools = self._db.get_all_tools()
        self._count_label.configure(text=f"{len(tools)} tool{'s' if len(tools) != 1 else ''}")

        if not tools:
            empty = ctk.CTkLabel(
                self._scroll_frame,
                text="No tools added yet.\nAdd your first tool above to get started!",
                font=ctk.CTkFont(size=14), text_color=COLOR_TEXT_DIM,
                justify="center",
            )
            empty.pack(pady=40)
            return

        for tool in tools:
            self._create_tool_card(tool)

    def _create_tool_card(self, tool: dict):
        """Render a single tool as a styled card."""
        card = ctk.CTkFrame(
            self._scroll_frame, fg_color=COLOR_CARD,
            corner_radius=12, border_width=1, border_color=COLOR_BORDER,
            height=80,
        )
        card.pack(fill="x", pady=(0, 8))
        card.pack_propagate(False)

        # Left info section
        info = ctk.CTkFrame(card, fg_color="transparent")
        info.pack(side="left", fill="both", expand=True, padx=16, pady=12)

        name_label = ctk.CTkLabel(
            info, text=tool["name"],
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color=COLOR_TEXT, anchor="w",
        )
        name_label.pack(fill="x")

        desc_label = ctk.CTkLabel(
            info, text=tool["description"],
            font=ctk.CTkFont(size=12), text_color=COLOR_TEXT_DIM, anchor="w",
        )
        desc_label.pack(fill="x")

        link_label = ctk.CTkLabel(
            info, text=tool["affiliate_link"],
            font=ctk.CTkFont(size=11), text_color=COLOR_ACCENT, anchor="w",
        )
        link_label.pack(fill="x")

        # Delete button on the right
        del_btn = ctk.CTkButton(
            card, text="🗑", width=40, height=40,
            font=ctk.CTkFont(size=16),
            fg_color="transparent", hover_color="#3a1a1a",
            text_color=COLOR_RED, corner_radius=8,
            command=lambda tid=tool["id"]: self._delete_tool(tid),
        )
        del_btn.pack(side="right", padx=12)
