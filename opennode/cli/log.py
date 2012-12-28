import logging
import logging.handlers
import os
import inspect
from opennode.cli.config import get_config

_logger = None

def get_logger(level=None):
    global _logger
    if _logger is None:
        _logger = Logger(level=level)
        return _logger
    return _logger

class Logger():
    """ Wrapper around standard logger, configured for our use case """
    logger = None
    def __init__(self, logger = None, level=None):
        # For future: find a safe way to use external std logger facility
        if logger is None:
            self.logger = logging.getLogger('opennode-tui')
            conf_level = get_config().getstring('general', 'loglevel', 'INFO')
            if level is None:
                try:
                    level_nr = logging._levelNames[conf_level.upper()]
                except KeyError:
                    level_nr = logging.INFO
            else:
                try:
                    level_nr = logging._levelNames[level.upper()]
                except KeyError:
                    level_nr = logging.INFO
            self.logger.setLevel(level_nr)
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
