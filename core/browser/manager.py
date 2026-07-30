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

    def start(self, headless: bool = False) -> webdriver.Chrome:
        """
        Ensures Chrome is running natively, then connects Selenium 4 to it.
        Returns the active webdriver instance.
        """
        logger.info(f"Launching Chrome via native Selenium (Headless: {headless})...")
        chrome_options = Options()
        chrome_options.add_argument(f"--user-data-dir={self.config.USER_DATA_DIR}")
        
        # Standard fixes for stability
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        
        if headless:
            chrome_options.add_argument("--headless=new")
        
        # Optional: Prevent Chrome from displaying 'Chrome is being controlled by automated software'
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        try:
            logger.info("Initializing webdriver.Chrome() (This might take a moment)...")
            self.driver = webdriver.Chrome(options=chrome_options)
            logger.info("Successfully connected to Chrome via Selenium.")
            return self.driver
        except Exception as e:
            error_msg = f"Failed to launch Chrome: {str(e)}"
            logger.error(error_msg)
            raise SeleniumConnectionError(error_msg) from e

    def _ensure_driver(self) -> None:
        """Helper to ensure driver is initialized before calling browser methods."""
        if self.driver is None:
            raise RuntimeError("BrowserManager has not been started. Call start() first.")

    def goto(self, url: str) -> None:
        """Navigates the current tab to the specified URL."""
        self._ensure_driver()
        logger.info(f"Navigating to: {url}")
        self.driver.get(url)

    def inject_cookies(self, cookies: list, domain: str) -> None:
        """
        Injects a list of JSON cookies into the browser for the specified domain.
        Must be called AFTER navigating to the domain (e.g. self.goto('https://reddit.com'))
        """
        self._ensure_driver()
        logger.info(f"Injecting {len(cookies)} cookies into {domain}...")
        for cookie in cookies:
            try:
                # Selenium requires 'name' and 'value', and optionally 'domain', 'path', 'secure', 'expiry'
                # Clean up cookie dict to match Selenium's expected format
                c = {
                    'name': cookie.get('name', ''),
                    'value': cookie.get('value', ''),
                    'domain': cookie.get('domain', ''),
                    'path': cookie.get('path', '/')
                }
                if 'secure' in cookie:
                    c['secure'] = cookie['secure']
                if 'expirationDate' in cookie:
                    c['expiry'] = int(cookie['expirationDate'])
                
                self.driver.add_cookie(c)
            except Exception as e:
                logger.warning(f"Failed to inject cookie {cookie.get('name')}: {e}")
        
        logger.info("Cookies injected successfully. Refreshing page to apply...")
        self.driver.refresh()

    def get_requests_session(self) -> __import__('requests').Session:
        """
        Extracts cookies from the current Selenium session and returns a ready-to-use requests.Session.
        This allows lightning-fast API scraping using the authenticated browser session.
        """
        self._ensure_driver()
        import requests
        session = requests.Session()
        # Set a standard User-Agent to avoid generic bot blocking
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })
        
        selenium_cookies = self.driver.get_cookies()
        for cookie in selenium_cookies:
            session.cookies.set(cookie['name'], cookie['value'], domain=cookie.get('domain', ''))
            
        return session

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
