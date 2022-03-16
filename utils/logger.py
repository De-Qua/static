from pathlib import Path
import logging
from logging.handlers import RotatingFileHandler


def get_logger(name="dequa_update", file='logs/automatic_tasks.log', level=logging.DEBUG):
    logger = logging.getLogger(name)
    logger.setLevel(level)
    log_file = Path(file)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(log_file, maxBytes=100000, backupCount=10)
    formatter = logging.Formatter('[%(asctime)s] [%(name)s:%(filename)s:%(lineno)d] [%(levelname)s] %(message)s')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)
    logger.addHandler(file_handler)
    return logger
