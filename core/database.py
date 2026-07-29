"""
database.py — SQLite Database Helper

Manages three tables:
  - tools: Affiliate tools (name, description, link)
  - settings: Key-value store for API keys and config
  - processed_posts: Tracks Reddit post IDs already handled

Thread safety: Each method opens its own connection so the bot thread
and the GUI thread never share a connection object.
"""

import sqlite3
import os
from datetime import datetime


class Database:
    """SQLite wrapper for the AI Affiliate Marketing Bot."""

    def __init__(self, db_path: str = None):
        # Default: store the DB next to the running script
        if db_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(base_dir, "bot_data.db")
        self.db_path = db_path
        self._create_tables()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        """Open a new connection (safe to call from any thread)."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # dict-like access
        return conn

    def _create_tables(self):
        """Auto-create tables on first run if they don't exist."""
        conn = self._connect()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tools (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT    NOT NULL,
                description TEXT    NOT NULL,
                affiliate_link TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS processed_posts (
                post_id      TEXT PRIMARY KEY,
                processed_at TEXT NOT NULL
            )
        """)

        conn.commit()
        conn.close()

    # ------------------------------------------------------------------
    # Tools CRUD
    # ------------------------------------------------------------------

    def add_tool(self, name: str, description: str, affiliate_link: str) -> int:
        """Insert a new tool and return its row ID."""
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO tools (name, description, affiliate_link) VALUES (?, ?, ?)",
            (name, description, affiliate_link),
        )
        conn.commit()
        row_id = cursor.lastrowid
        conn.close()
        return row_id

    def delete_tool(self, tool_id: int):
        """Delete a tool by its ID."""
        conn = self._connect()
        conn.execute("DELETE FROM tools WHERE id = ?", (tool_id,))
        conn.commit()
        conn.close()

    def get_all_tools(self) -> list[dict]:
        """Return every tool as a list of dicts."""
        conn = self._connect()
        rows = conn.execute("SELECT id, name, description, affiliate_link FROM tools").fetchall()
        conn.close()
        return [dict(row) for row in rows]

    # ------------------------------------------------------------------
    # Settings (key-value)
    # ------------------------------------------------------------------

    def save_setting(self, key: str, value: str):
        """Upsert a single setting."""
        conn = self._connect()
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, value),
        )
        conn.commit()
        conn.close()

    def get_setting(self, key: str, default: str = None) -> str | None:
        """Retrieve a single setting, or *default* if not found."""
        conn = self._connect()
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        conn.close()
        return row["value"] if row else default

    def get_all_settings(self) -> dict[str, str]:
        """Return all settings as a flat dict."""
        conn = self._connect()
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
        conn.close()
        return {row["key"]: row["value"] for row in rows}

    # ------------------------------------------------------------------
    # Processed posts
    # ------------------------------------------------------------------

    def is_post_processed(self, post_id: str) -> bool:
        """Check whether a Reddit post has already been handled."""
        conn = self._connect()
        row = conn.execute(
            "SELECT 1 FROM processed_posts WHERE post_id = ?", (post_id,)
        ).fetchone()
        conn.close()
        return row is not None

    def mark_post_processed(self, post_id: str):
        """Record a post ID so we skip it in future sweeps."""
        conn = self._connect()
        conn.execute(
            "INSERT OR IGNORE INTO processed_posts (post_id, processed_at) VALUES (?, ?)",
            (post_id, datetime.utcnow().isoformat()),
        )
        conn.commit()
        conn.close()
