"""
Utility functions and custom exceptions for the Browser Manager.
"""
import socket
import logging

# Set up standard logger
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

class ChromeExecutableNotFoundError(Exception):
    """Raised when the Chrome executable cannot be found at the specified path."""
    pass

class ProfileNotFoundError(Exception):
    """Raised when the specified Chrome User Data Directory or Profile is missing."""
    pass

class SeleniumConnectionError(Exception):
    """Raised when Selenium fails to connect to the Chrome remote debugging port."""
    pass

class ChromeLaunchTimeoutError(Exception):
    """Raised when Chrome fails to launch or bind to the debugging port in time."""
    pass

def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """
    Checks if a given port is currently open and responding.
    Returns True if Chrome (or another process) is listening on this port.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1.0)
        result = s.connect_ex((host, port))
        return result == 0
