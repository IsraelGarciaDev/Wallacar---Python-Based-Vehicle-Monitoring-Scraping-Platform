import os
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, DB_NAME, DEFAULT_MIN_PRICE
from logger import logger

def test_config():
    logger.info("🧪 Testing Configuration Loading...")
    
    logger.info(f"DB_NAME: {DB_NAME}")
    logger.info(f"DEFAULT_MIN_PRICE: {DEFAULT_MIN_PRICE}")
    
    if TELEGRAM_TOKEN:
        logger.info("✅ TELEGRAM_TOKEN found.")
    else:
        logger.warning("❌ TELEGRAM_TOKEN is missing (check .env).")
        
    if TELEGRAM_CHAT_ID:
        logger.info("✅ TELEGRAM_CHAT_ID found.")
    else:
        logger.warning("❌ TELEGRAM_CHAT_ID is missing (check .env).")

    logger.info("Config Check Completed.")

if __name__ == "__main__":
    test_config()
