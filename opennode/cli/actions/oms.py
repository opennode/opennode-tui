import ConfigParser

from opennode.cli.actions.utils import execute
from opennode.cli import config


def get_oms_server():
    """Read OMS server port and address from the configuration file"""
    minion_conf_file = config.c('general', 'minion-conf')
    minion_config = ConfigParser.RawConfigParser()
    minion_config.read(minion_conf_file)
    try:
        oms_server = minion_config.get('main', 'certmaster')
        oms_server_port = minion_config.get('main', 'certmaster_port')
        return (oms_server, oms_server_port)
    except ConfigParser.NoOptionError:
        return ('', '')


def set_oms_server(server, port=51235):
    """Write OMS server address and port to the configuration file"""
    minion_conf_file = config.c('general', 'minion-conf')
    minion_config = ConfigParser.RawConfigParser()
    minion_config.read(minion_conf_file)
    minion_config.set('main', 'certmaster', server)
    minion_config.set('main', 'certmaster_port', port)
    with open(minion_conf_file, 'w') as conf:
        minion_config.write(conf)


def register_oms_server(server, port):
    """Register with a new OMS server:port."""
    set_oms_server(server, port)
    execute('service funcd restart')
