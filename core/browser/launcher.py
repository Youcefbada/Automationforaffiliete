"""
Launcher module responsible for validating paths and launching Chrome 
with the correct CDP (Remote Debugging) flags.
"""
import os
import time
import subprocess
from core.browser.config import ChromeConfig
from core.browser.utils import (
    logger,
    is_port_in_use,
    ChromeExecutableNotFoundError,
    ProfileNotFoundError,
    ChromeLaunchTimeoutError
)

def wait_for_port(port: int, host: str = "127.0.0.1", timeout: int = 15) -> bool:
    """
    Polls the given port until it opens or the timeout is reached.
    Avoids using a blind time.sleep() by constantly checking.
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        if is_port_in_use(port, host):
            return True
        time.sleep(0.5)
    return False

def launch_chrome_if_needed(config: ChromeConfig) -> None:
    """
    Checks if Chrome is already listening on the debugging port.
    If not, validates paths and launches Chrome as a subprocess.
    """
    if is_port_in_use(config.DEBUG_PORT, config.DEBUG_HOST):
        logger.info(f"Chrome is already running on port {config.DEBUG_PORT}. Will connect immediately.")
        return

    logger.info("Chrome is not running on the debug port. Preparing to launch...")

    # 1. Validate Executable
    if not os.path.exists(config.EXECUTABLE_PATH):
        logger.error("Chrome executable not found.")
        raise ChromeExecutableNotFoundError(f"Missing: {config.EXECUTABLE_PATH}")

    # 2. Validate User Data Directory
    if not os.path.exists(config.USER_DATA_DIR):
        logger.error("User Data directory not found.")
        raise ProfileNotFoundError(f"Missing: {config.USER_DATA_DIR}")

    # 3. Build command arguments
    command = [
        config.EXECUTABLE_PATH,
        f"--remote-debugging-port={config.DEBUG_PORT}",
        f"--user-data-dir={config.USER_DATA_DIR}",
        f"--profile-directory={config.PROFILE_DIR}"
    ]

    logger.info("Launching Chrome...")
    try:
        # Launch Chrome. Removing DEVNULL so we can capture any stdout/stderr errors.
        process = subprocess.Popen(command)
    except Exception as e:
        logger.error(f"Failed to launch Chrome subprocess: {e}")
        raise

    # 4. Wait for Chrome to bind to the port (Max 15 seconds)
    logger.info("Waiting for Chrome to become available...")
    if not wait_for_port(config.DEBUG_PORT, config.DEBUG_HOST):
        logger.error("Timeout: Chrome did not respond on the debug port.")
        raise ChromeLaunchTimeoutError(
            f"Chrome launched but port {config.DEBUG_PORT} did not open within 15 seconds. "
            "Please ensure all other normal Chrome windows are closed before running this."
        )
    
    logger.info(f"Chrome successfully launched and listening on port {config.DEBUG_PORT}.")
