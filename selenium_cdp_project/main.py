"""
Example usage script for the Selenium CDP Browser Manager.
"""
import time
from browser.manager import BrowserManager
from browser.utils import logger

def main() -> None:
    # 1. Initialize the manager
    logger.info("Initializing BrowserManager...")
    browser = BrowserManager()

    try:
        # 2. Start (or connect to) the existing Chrome profile
        driver = browser.start()
        
        # 3. Navigate the main tab
        browser.goto("https://github.com")
        
        # 4. Open new tabs
        time.sleep(2)  # Short pause just for visual effect in this demo
        browser.open_tab("https://chat.openai.com")
        
        time.sleep(2)
        browser.open_tab("https://linkedin.com")

        # 5. Print the current tab's URL
        logger.info(f"Currently viewing: {browser.current_tab()}")

        # 6. Switch back to the first tab (Github)
        time.sleep(2)
        browser.switch(0)
        logger.info(f"Switched back to: {browser.current_tab()}")
        
        # 7. Close the Github tab
        time.sleep(2)
        browser.close_tab()

    except Exception as e:
        logger.error(f"An error occurred during execution: {e}")
    finally:
        # 8. Disconnect Selenium (keeps the Chrome window open!)
        browser.quit()
        logger.info("Demo complete. Chrome remains open for your manual use.")

if __name__ == "__main__":
    main()
