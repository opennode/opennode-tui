import ConfigParser
import os

config_path = '/etc/opennode/'

config_names = {'global': 'opennode-tui.conf',
           'openvz': 'openvz.conf',
           'kvm': 'kvm.conf'}


def _resolve_conf_name(conf_type):
    """
    Return a filename of the configuration file. Local file has a higher
    priority than in the config_path.
    """
    fnm = config_names[conf_type]
    if os.path.isfile(fnm):
        return fnm
    elif os.path.isfile(config_path + fnm):
        return config_path + fnm
    else:
        raise RuntimeError("Missing configuration file for %s" % conf_type)


def c(group, field, conf_type='global'):
    """Get configuration value"""
    conf = ConfigParser.RawConfigParser()
    conf.read(_resolve_conf_name(conf_type))
    return conf.get(group, field)


def cs(group, field, value, conf_type='global'):
    """Set configuration value"""
    conf = ConfigParser.RawConfigParser()
    fnm = _resolve_conf_name(conf_type)
    conf.read(fnm)
    conf.set(group, field, value)
    with open(fnm, 'wb') as configfile:
        conf.write(configfile)


def clist(group, conf_type='global'):
    """List configuration values"""
    conf = ConfigParser.RawConfigParser()
    conf.read(_resolve_conf_name(conf_type))
    return conf.items(group)


def has_option(group, field, conf_type='global'):
    """Return whether an option is available for that section"""
    conf = ConfigParser.RawConfigParser()
    conf.read(_resolve_conf_name(conf_type))
    return conf.has_option(group, field)
