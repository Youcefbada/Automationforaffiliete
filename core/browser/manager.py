"""
The core BrowserManager class that wraps Selenium 4.
It handles connecting to the local CDP port and managing tabs.
"""
from typing import Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

from core.browser.config import ChromeConfig
from core.browser.utils import logger, SeleniumConnectionError

class BrowserManager:
    def __init__(self) -> None:
        """Initializes the configuration for the Browser Manager."""
        self.config = ChromeConfig()
        self.driver: Optional[webdriver.Chrome] = None

    def start(self) -> webdriver.Chrome:
        """
        Ensures Chrome is running on the debug port, then connects Selenium 4 to it.
        Returns the active webdriver instance.
        """
        logger.info("Launching Chrome via native Selenium...")
        chrome_options = Options()
        chrome_options.add_argument(f"--user-data-dir={self.config.USER_DATA_DIR}")
        chrome_options.add_argument(f"--profile-directory={self.config.PROFILE_DIR}")
        # Optional: Prevent Chrome from displaying 'Chrome is being controlled by automated software'
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            logger.info("Successfully connected to Chrome via Selenium.")
            return self.driver
        except Exception as e:
            logger.error(f"Failed to launch Chrome. Please ensure ALL Chrome windows are fully closed! Error: {e}")
            raise SeleniumConnectionError(f"Could not launch Chrome. Is it already running?") from e

    def _ensure_driver(self) -> None:
        """Helper to ensure driver is initialized before calling browser methods."""
        if self.driver is None:
            raise RuntimeError("BrowserManager has not been started. Call start() first.")

    def goto(self, url: str) -> None:
        """Navigates the current tab to the specified URL."""
        self._ensure_driver()
        logger.info(f"Navigating to: {url}")
        self.driver.get(url)

    def open_tab(self, url: str) -> None:
        """Opens a new tab and navigates to the specified URL."""
        self._ensure_driver()
        logger.info(f"Opening new tab: {url}")
        # Selenium 4 native new window command
        self.driver.switch_to.new_window('tab')
        self.driver.get(url)

    def close_tab(self) -> None:
        """Closes the current tab and switches to the last available tab."""
        self._ensure_driver()
        logger.info("Closing current tab...")
        self.driver.close()
        
        # Switch back to the last available window handle to avoid Orphaned Window errors
        handles = self.driver.window_handles
        if handles:
            self.switch(len(handles) - 1)

    def current_tab(self) -> str:
        """Returns the URL of the current tab."""
        self._ensure_driver()
        return self.driver.current_url

    def switch(self, index: int) -> None:
        """Switches focus to the tab at the given index (0-based)."""
        self._ensure_driver()
        handles = self.driver.window_handles
        if index < 0 or index >= len(handles):
            raise IndexError(f"Tab index {index} out of range. Total tabs: {len(handles)}")
        
        logger.info(f"Switching to tab index {index}...")
        self.driver.switch_to.window(handles[index])

    def quit(self) -> None:
        """Disconnects Selenium from the browser (Does NOT kill the Chrome process)."""
        self._ensure_driver()
        logger.info("Disconnecting Selenium from Chrome...")
        self.driver.quit()
        self.driver = None
