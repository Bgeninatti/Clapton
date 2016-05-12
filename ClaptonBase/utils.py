# -*- coding: utf-8 -*-
import logging, time
from logging.handlers import RotatingFileHandler
from threading import _Event
from cfg import *


def get_logger(logger_name, log_level=None, log_file=None, backup_count=1):
    logger = logging.getLogger(logger_name)
    if not logger.handlers:
        if log_level is not None:
            level = getattr(logging, log_level.upper(), logging.INFO)
        else:
            level = logging.INFO
        if log_file is None:
            handler = logging.StreamHandler()
        else:
            handler = RotatingFileHandler(log_file, backupCount=backup_count)
        handler.setLevel(level)
        fmt = ("%(asctime)s - %(process)d/%(threadName)s - %(name)s:%(module)s.%(funcName)s [%(levelname)s] %(message)s")
        handler.setFormatter(logging.Formatter(fmt))
        logger.addHandler(handler)
        logger.setLevel(level)

    return logger


class MasterEvent(_Event):

    def __init__(self, *args, **kwargs):
        super(MasterEvent, self).__init__(*args, **kwargs)
        self.timeout = None

    def set(self, *args, **kwargs):
        super(MasterEvent, self).set()
        self.timeout = time.time() + MASTER_EVENT_TIMEOUT

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