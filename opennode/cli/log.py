import logging
import logging.handlers
import sys

from opennode.cli.config import get_config

_logger = None
_configured = False

def _configure():
    logger = get_logger()
    global _configured

    if not getattr(logger, '_configured', False) and not _configured:
        conf_level = get_config().getstring('general', 'loglevel', 'INFO')
        level = logging._levelNames.get(conf_level.upper())
        if level is None:
            level = logging.INFO

        logger.setLevel(level)

        fh = logging.handlers.WatchedFileHandler(get_config().getstring('general', 'log-location',
                                                                        '/var/log/opennode-tui.log'))
        format_str = '%(asctime)s %(levelname)7s %(module)10s:%(lineno)s:%(funcName)s - %(message)s'
        fhformatter = logging.Formatter(format_str)
        fh.setFormatter(fhformatter)
        logger.addHandler(fh)

        sh = logging.StreamHandler(sys.stdout)
        sh.setLevel(logging.INFO)
        sh.setFormatter(logging.Formatter('%(message)s'))
        logger.addHandler(sh)

        sherr = logging.StreamHandler()
        sherr.setLevel(logging.ERROR)
        sherr.setFormatter(logging.Formatter('%(module)10s:%(lineno)s:%(funcName)s - %(message)s'))
        logger.addHandler(sherr)

        _configured = True


_configure()


def get_logger(level=None):
    logger = logging.getLogger('opennode-tui')
    if level is not None:
        logger.setLevel(level)
    return logger
