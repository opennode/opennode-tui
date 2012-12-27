import logging
import logging.handlers
import os
import inspect
from opennode.cli.config import get_config

_logger = None

def get_logger():
    global _logger
    if _logger is None:
        _logger = Logger()
        return _logger
    return _logger

class Logger():
    """ Wrapper around standard logger, configured for our use case """
    logger = None
    def __init__(self, logger = None, level=0):
        # For future: find a safe way to use external std logger facility
        if logger is None:
            self.logger = logging.getLogger('opennode-tui')
            self.logger.setLevel(logging.DEBUG)
            self.format_str = '%(asctime)s - %(levelname)7s - %(stack)14s - %(message)s'
            self.formatter = logging.Formatter(self.format_str)
            self.fh = logging.handlers.WatchedFileHandler(get_config().getstring('general', 'log-location',
                                                                                 '/var/log/opennode-tui.log'))
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
