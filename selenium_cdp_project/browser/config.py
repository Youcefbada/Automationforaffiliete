"""
Configuration constants for the Browser Manager.
Defines paths and ports required for Chrome Remote Debugging on Windows.
"""
from dataclasses import dataclass

@dataclass(frozen=True)
class ChromeConfig:
    """Dataclass storing Chrome configuration details."""
    EXECUTABLE_PATH: str = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    USER_DATA_DIR: str = r"C:\Users\Youcef\AppData\Local\Google\Chrome\User Data"
    PROFILE_DIR: str = "Profile 19"
    DEBUG_PORT: int = 9222
    DEBUG_HOST: str = "127.0.0.1"
    
    @property
    def debugger_address(self) -> str:
        """Returns the formatted debugger address."""
        return f"{self.DEBUG_HOST}:{self.DEBUG_PORT}"
