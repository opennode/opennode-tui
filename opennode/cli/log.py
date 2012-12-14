import logging
import os
import inspect
from opennode.cli.config import get_config

_logger = None

def get_logger():
    global _logger
    if _logger is None:
        _logger = Logger('opennode-tui')
        return _logger
    return _logger


class Logger():
    """ Signleton logging class """
    logger = None
    def __init__(self, log_source):
        self.logger = logging.getLogger(log_source)
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

    # TODO: if need rises, add additional log levels.
    # log_* methods are wrappers around conventional log methods with stack inspection.
    # inspect.stack() is needed to get filename where logging command came from.
    def log_debug(self, text, *args):
        stack = {'stack': os.path.basename(inspect.stack()[1][1])}
        self.logger.debug(text, *args, extra=stack)

    def log_info(self, text, *args):
        stack = {'stack': os.path.basename(inspect.stack()[1][1])}
        self.logger.info(text, *args, extra=stack)

    def log_warn(self, text, *args):
        stack = {'stack': os.path.basename(inspect.stack()[1][1])}
        self.logger.warning(text, *args, extra=stack)

    def log_error(self, text, *args):
        stack = {'stack': os.path.basename(inspect.stack()[1][1])}
        self.logger.error(text, *args, extra=stack)
