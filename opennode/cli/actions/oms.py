import ConfigParser
import socket
import subprocess

from opennode.cli.config import c

def get_oms_server():
    """Read OMS server port and address from the configuration file"""
    minion_conf_file = c('general', 'minion-conf')
    minion_config = ConfigParser.RawConfigParser()
    minion_config.read(minion_conf_file)
    try:
        oms_server = minion_config.get('main', 'certmaster')
        oms_server_port = minion_config.get('main', 'certmaster_port')
        return (oms_server, oms_server_port)
    except ConfigParser.NoOptionError:
        return ('', '') 

def set_oms_server(server, port = 51235):
    """Write OMS server address and port to the configuration file"""
    minion_conf_file = c('general', 'minion-conf')
    minion_config = ConfigParser.RawConfigParser()
    minion_config.read(minion_conf_file)
    minion_config.set('main', 'certmaster', server)
    minion_config.set('main', 'certmaster_port', port)

def validate_oms_server(server, port):
    """Validate server name and port of the OMS server. Return True/False"""
    # make sure that we can find at least one way of connecting to the system
    try:
        return len(socket.getaddrinfo(server, port)) > 1
    except socket.gaierror:
        return False

def register_oms_server(server, port):
    """Register with a new OMS server:port."""
    set_oms_server(server, port)
    # XXX: need to add reasonable logging to a file
    subprocess.call(['service', 'funcd', 'restart'])

