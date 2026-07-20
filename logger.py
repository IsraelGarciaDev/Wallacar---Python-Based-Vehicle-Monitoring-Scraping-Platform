import logging
import os
from logging.handlers import RotatingFileHandler
from rich.logging import RichHandler

# Ensure logs directory exists
LOGS_DIR = "logs"
os.makedirs(LOGS_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOGS_DIR, "app.log")

def setup_logger(name: str = "WallapopBot", level: int = logging.INFO) -> logging.Logger:
    """
    Configures and returns a logger instance with RichHandler for console
    and RotatingFileHandler for file output.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Prevent adding handlers multiple times
    if logger.hasHandlers():
        return logger

    # Formatters
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Console Handler (Rich)
    console_handler = RichHandler(
        rich_tracebacks=True,
        show_path=False,
        markup=True
    )
    console_handler.setLevel(level)

    # File Handler (Rotating)
    # Max size 5MB, keep 3 backups
    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=5*1024*1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(file_formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger

# Create a default logger instance
logger = setup_logger()
