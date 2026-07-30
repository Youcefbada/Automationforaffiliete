import time
from core.bot import BotEngine
from core.database import Database

class DummyUI:
    def log(self, message):
        print(message)
        
    def after(self, ms, func):
        pass

if __name__ == "__main__":
    db = Database()
    ui = DummyUI()
    engine = BotEngine(db, ui)
    
    print("Starting bot engine in headless mode...")
    engine.start()
    
    try:
        while engine.is_running():
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping bot engine...")
        engine.stop()
