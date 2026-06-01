import logging
import os

from core.constants import LOG_DIR

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

def setup_logger(name: str = __name__, log_file: str = None) -> logging.Logger:
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    return logger

def get_import_logger() -> logging.Logger:
    log_file = os.path.join(LOG_DIR, "import.log")
    return setup_logger("chat_import", log_file)

def get_analysis_logger() -> logging.Logger:
    log_file = os.path.join(LOG_DIR, "analysis.log")
    return setup_logger("analysis", log_file)

def get_default_logger() -> logging.Logger:
    return setup_logger(__name__)
