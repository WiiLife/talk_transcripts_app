import logging
import os

class ColorFormatter(logging.Formatter):
    """Custom formatter that colors debug messages."""
    COLORS = {
        logging.DEBUG: "\033[36m",   # Cyan
        logging.INFO: "\033[32m",    # Green
        logging.WARNING: "\033[33m", # Yellow
        logging.ERROR: "\033[31m",   # Red
        logging.CRITICAL: "\033[41m" # Red background
    }

    RESET = "\033[0m"

    def format(self, record):
        color = self.COLORS.get(record.levelno, self.RESET)
        message = super().format(record)
        return f"{color}{message}{self.RESET}"

def setup_logging():
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    
    # DEBUG LOGGER
    debug_logger = logging.getLogger("debug_logger")
    debug_logger.setLevel(logging.DEBUG)
    debug_logger.propagate = False

    debug_handler = logging.StreamHandler()
    debug_handler.setLevel(logging.DEBUG)
    debug_handler.setFormatter(
        ColorFormatter("%(asctime)s [%(levelname)s] %(message)s")
    )

    if log_level == "DEBUG":
        debug_logger.addHandler(debug_handler)

    # INFO LOGGER
    info_logger = logging.getLogger("info_logger")
    info_logger.setLevel(logging.INFO)
    info_logger.propagate = False

    info_handler = logging.StreamHandler()
    info_handler.setLevel(logging.INFO)
    info_handler.setFormatter(
        ColorFormatter("%(asctime)s [%(levelname)s] %(message)s")
    )

    if log_level != "DEBUG":
        info_logger.addHandler(info_handler)
