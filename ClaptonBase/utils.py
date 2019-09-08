# -*- coding: utf-8 -*-
import logging
import logging.config
from . import cfg


loggers = {}

def get_logger(name):
    if name in loggers.keys():
        return loggers[name]
    MAIN_FORMAT = ("%(asctime)s - %(process)d/%(threadName)s - %(lineno)d in %(filename)s" +
                   " [%(levelname)s] %(message)s")
    LOG_CONFIG = {'version': 1,
                  'formatters': {'error': {'format': MAIN_FORMAT},
                                 'info': {'format': MAIN_FORMAT},
                                 'debug': {'format': MAIN_FORMAT}},
                  'handlers': {'console': {'class': 'logging.StreamHandler',
                                           'formatter': 'info',
                                           'level': cfg.LOG_LEVEL}},
                  'root': {'handlers': ('console',), 'level': 'DEBUG'}}
    logging.config.dictConfig(LOG_CONFIG)
    logger = logging.getLogger(name)
    logger.setLevel(cfg.LOG_LEVEL)
    loggers[name] = logger
    return logger

