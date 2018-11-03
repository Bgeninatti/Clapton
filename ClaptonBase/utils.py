# -*- coding: utf-8 -*-
import logging
import logging.config
import time
try:
    from threading import _Event as Event
except ImportError:
    from threading import Event
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


class MasterEvent(Event):

    def __init__(self, *args, **kwargs):
        super(MasterEvent, self).__init__(*args, **kwargs)
        self.timeout = None

    def set(self, *args, **kwargs):
        super(MasterEvent, self).set()
        self.timeout = time.time() + cfg.MASTER_EVENT_TIMEOUT

    def clear(self, *args, **kwargs):
        self.timeout = None
        super(MasterEvent, self).clear()


class GiveMasterEvent(MasterEvent):

    def __init__(self, *args, **kwargs):
        super(GiveMasterEvent, self).__init__(*args, **kwargs)
        self.node = None

    def set(self, node, *args, **kwargs):
        super(GiveMasterEvent, self).set()
        self.node = node

    def clear(self, *args, **kwargs):
        self.node = None
        super(GiveMasterEvent, self).clear(*args, **kwargs)
