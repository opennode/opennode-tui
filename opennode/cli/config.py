import ConfigParser

config_paths = {'global': 'opennode-tui.conf', #'/etc/opennode/opennode-tui.conf',
           'openvz': 'openvz.conf', #'/etc/opennode/openvz.conf',
           'kvm': '/etc/opennode/kvm.conf'}

def c(group, field, config = 'global'):
    """Get configuration value"""
    conf = ConfigParser.RawConfigParser()
    conf.read(config_paths[config])
    return conf.get(group, field)

def cs(group, field, value, config = 'global'):
    """Set configuration value"""
    conf = ConfigParser.RawConfigParser()
    conf.read(config_paths[config])
    conf.set(group, field, value)
    with open(config_paths[config], 'wb') as configfile:
        conf.write(configfile)

def clist(group, config = 'global'):
    """List configuration values"""
    conf = ConfigParser.RawConfigParser()
    conf.read(config_paths[config])
    return conf.items(group)

