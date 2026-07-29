"""
logger.py — Thread-Safe GUI Logger

Uses a queue.Queue to bridge the bot thread and the GUI thread.
The bot calls `log()` from any thread; the GUI polls `get_messages()`
via tkinter's `after()` method to safely update the CTkTextbox.
"""

import queue
from datetime import datetime


class LogManager:
    """Thread-safe message queue for live GUI logging."""

    def __init__(self):
        self._queue: queue.Queue[str] = queue.Queue()

    def log(self, message: str):
        """
        Push a timestamped message onto the queue.
        Safe to call from any thread.
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._queue.put(f"[{timestamp}]  {message}")

    def get_messages(self) -> list[str]:
        """
        Drain all pending messages from the queue.
        Call this from the GUI thread only (inside an `after()` callback).
        Returns a list of formatted strings.
        """
        messages: list[str] = []
        while True:
            try:
                messages.append(self._queue.get_nowait())
            except queue.Empty:
                break
        return messages
