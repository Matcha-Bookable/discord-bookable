import logging
import os
from logging.handlers import RotatingFileHandler

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FILE = os.getenv("LOG_FILE", "bot.log")


def setup_logger(name: str = "discord_bookable") -> logging.Logger:
    """Configure and return a logger instance.

    Creates a rotating file handler and a console handler. Log format includes
    timestamp, level, module, and message. Subsequent calls return the same
    logger without adding duplicate handlers.
    """
    logger = logging.getLogger(name)
    if logger.handlers:  # Already configured
        return logger

    level = getattr(logging, LOG_LEVEL, logging.INFO)
    logger.setLevel(level)

    log_format = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(module)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(log_format)
    logger.addHandler(ch)

    # Rotating file handler (5 MB * 3 backups)
    try:
        fh = RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3)
        fh.setLevel(level)
        fh.setFormatter(log_format)
        logger.addHandler(fh)
    except OSError:
        # If file can't be created (permissions, read-only FS), continue with console only
        logger.warning("Failed to create log file '%s'. Proceeding with console logging only.", LOG_FILE)

    logger.debug("Logger initialized (level=%s, file=%s)", LOG_LEVEL, LOG_FILE)
    return logger
