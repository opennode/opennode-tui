import logging
import os
import inspect
from opennode.cli.config import get_config

def get_logger(ext_log = None, level = 0):
    if ext_log is None:
        return Logger(level=level)
    else:
        return Logger(ext_log, level=level)


class Logger():
    """ Signleton logging class """
    logger = None
    def __init__(self, logger = None, level=0):
        if logger is None:
            self.logger = logging.getLogger('opennode-tui')
            self.logger.setLevel(logging.DEBUG)
            self.format_str = '%(asctime)s - %(levelname)7s - %(stack)14s - %(message)s'
            self.formatter = logging.Formatter(self.format_str)

            self.fh = logging.FileHandler(get_config().getstring('general', 'log-location', '/var/log/opennode-tui.log'))
            self.fh.setLevel(logging.DEBUG)
            self.fh.setFormatter(self.formatter)
            self.ch = logging.StreamHandler()
            self.ch.setLevel(logging.ERROR)
            self.ch.setFormatter(self.formatter)
            self.logger.addHandler(self.fh)
            self.logger.addHandler(self.ch)
        else:
            self.logger = logger
        if level:
            self.logger.setLevel(level)

    # TODO: if need rises, add additional log levels.
    # inspect.stack() is needed to get filename where logging command came from.
    def debug(self, text, *args):
        stack = {'stack': os.path.basename(inspect.stack()[1][1])}
        self.logger.debug(text, *args, extra=stack)

    def info(self, text, *args):
        stack = {'stack': os.path.basename(inspect.stack()[1][1])}
        self.logger.info(text, *args, extra=stack)

    def warn(self, text, *args):
        stack = {'stack': os.path.basename(inspect.stack()[1][1])}
        self.logger.warning(text, *args, extra=stack)

    def error(self, text, *args):
        stack = {'stack': os.path.basename(inspect.stack()[1][1])}
        self.logger.error(text, *args, extra=stack)

    def critical(self, text, *args):
        stack = {'stack': os.path.basename(inspect.stack()[1][1])}
        self.logger.critical(text, *args, extra=stack)
