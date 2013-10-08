import os
import yaml

from opennode.cli.config import get_config


def get_oms_server():
    """Read OMS server port and address from the configuration file"""
    minion_conf_file = get_config().getstring('general', 'salt-minion-conf')

    if not os.path.exists(minion_conf_file):
        minion_conf_file = '/etc/salt/minion'
        if not os.path.exists(minion_conf_file):
            return ('localhost', 4506)

    with open(minion_conf_file, 'r') as minion_conf:
        minion_config = yaml.safe_load(minion_conf.read())
        if minion_config is None:
            return ('localhost', 4506)
        oms_server = minion_config.get('master', 'localhost')
        oms_server_port = minion_config.get('master_port', 4506)
        return (oms_server, oms_server_port)


def set_oms_server(server, port=4506):
    """Write OMS server address and port to the configuration file"""
    minion_conf_file = get_config().getstring('general', 'salt-minion-conf')

    if not os.path.exists(minion_conf_file):
        minion_conf_file = '/etc/salt/minion'
        if not os.path.exists(minion_conf_file):
            return

    with open(minion_conf_file, 'r') as minion_conf:
        minion_config = yaml.safe_load(minion_conf.read())
        if minion_config is None:
            minion_config = {}
        minion_config['master'] = server
        minion_config['master_port'] = port
        minion_config['dns_retry'] = 0  # TUI-47

    with open(minion_conf_file, 'w') as conf:
        yaml.dump(minion_config, conf, default_flow_style=False)


def register_oms_server(server, port):
    """Register with a new OMS server:port."""
    # cleanup of the previous func cert
    set_oms_server(server, port)
    # XXX: actions.utils.execute2 does not work in this case and
    # actions.utils.execute hangs. With 'execute' python hangs
    # when reading back output of commands.getstatusoutput()
    os.popen('chkconfig salt-minion on')
    os.popen('service salt-minion restart')


## OMS VM specific ##
def configure_oms_vm(ctid, ipaddr):
    """Adjust configuration of the VM hosting OMS"""
    pass
    # this hook is not needed at the moment after migration from Func
    # however, keeping it here for the future use
