import logging
import colorlog


def get_logger(name="dequa_update", level=logging.DEBUG):
    logger = colorlog.getLogger(name)
    logger.handlers.clear()
    logger.setLevel(level)
    ch = colorlog.StreamHandler()
    formatter = colorlog.ColoredFormatter('[%(asctime)s] [%(name)s:%(filename)s:%(lineno)d] %(log_color)s[%(levelname)s]%(reset)s %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    return logger