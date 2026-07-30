"""
Configuration constants for the Browser Manager.
Defines paths and ports required for Chrome Remote Debugging on Windows.
"""
from dataclasses import dataclass
import os

@dataclass(frozen=True)
class ChromeConfig:
    """Dataclass storing Chrome configuration details."""
    EXECUTABLE_PATH: str = "" # Not needed for native Selenium
    USER_DATA_DIR: str = os.path.join(os.path.expanduser("~"), "Desktop", "automation_chrome_profile")
    DEBUG_HOST: str = "127.0.0.1"
    
    @property
    def debugger_address(self) -> str:
        """Returns the formatted debugger address."""
        return f"{self.DEBUG_HOST}:{self.DEBUG_PORT}"
