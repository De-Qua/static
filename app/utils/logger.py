import logging
import colorlog


def get_logger(name="dequa_update", level=logging.DEBUG):
    color_handler = colorlog.StreamHandler()
    formatter = colorlog.ColoredFormatter('[%(asctime)s] [%(name)s:%(filename)s:%(lineno)d] %(log_color)s[%(levelname)s]%(reset)s %(message)s')
    color_handler.setFormatter(formatter)
    
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(color_handler)
    # Third-party libraries (requests, urllib3, ...): only warnings and errors
    root_logger.setLevel(logging.WARNING)
    
    logging.getLogger("dequa_graph").setLevel(level)
        
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    return logger
