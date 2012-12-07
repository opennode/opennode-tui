from ConfigParser import ConfigParser, Error as ConfigKeyError, NoSectionError
from contextlib import closing
import os

config_path = '/etc/opennode/'

config_names = {'global': 'opennode-tui.conf',
                'openvz': 'openvz.conf',
                'kvm': 'kvm.conf'}

_config_object = {}


def get_config(config_type='global'):
    global _config_object
    if not _config_object.get(config_type, None):
        _config_object[config_type] = TUIConfig(config_type)
    return _config_object[config_type]


def gen_config_file_names():
    config_path = '/etc/opennode/'
    config_types = ['global', 'openvz', 'kvm']
    config_names = ['opennode-tui.conf', 'openvz.conf', 'kvm.conf']
    return dict(zip(config_types, [os.path.join(config_path,
                                                i) for i in config_names]))


class TUIConfig(ConfigParser):
    no_default = object()

    def __init__(self, config_type, path=config_path, names=config_names):
        ConfigParser.__init__(self)
        self.config_path = path
        self.config_names = names
        self.config_type = config_type
        self.config_file = gen_config_file_names()[self.config_type]
        with closing(open(self.config_file)) as f:
            self.readfp(f)

    def getboolean(self, section, option, default=no_default):
        try:
            return ConfigParser.getboolean(self, section, option)
        except ConfigKeyError:
            if default is not self.no_default:
                return default
            print 'CANNOT FIND CONF KEY', section, option
            raise

    def getint(self, section, option, default=no_default):
        try:
            return ConfigParser.getint(self, section, option)
        except ConfigKeyError:
            if default is not self.no_default:
                return default
            print 'CANNOT FIND CONF KEY', section, option
            raise

    def getfloat(self, section, option, default=no_default):
        try:
            return ConfigParser.getfloat(self, section, option)
        except ConfigKeyError:
            if default is not self.no_default:
                return default
            print 'CANNOT FIND CONF KEY', section, option
            raise

    def getstring(self, section, option, default=no_default):
        try:
            return ConfigParser.get(self, section, option)
        except ConfigKeyError:
            if default is not self.no_default:
                return default
            print 'CANNOT FIND CONF KEY', section, option
            raise

    def getlist(self, section, default=no_default):
        try:
            return ConfigParser.items(self, section)
        except ConfigKeyError:
            if default is not self.no_default:
                return default
            print 'CANNOT FIND CONF SECTION', section
            raise

    def setvalue(self, section, option, value):
        try:
            self.set(section, option, value)
            with closing(open(self.config_file, 'wt')) as f:
                self.write(f)
        except NoSectionError:
            self.add_section(section)
            self.setvalue(section, option, value)


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
    raise NotImplementedError('Use config.get_config([config_type]) and .get<type> methods')
    """Get configuration value"""
    conf = ConfigParser.RawConfigParser()
    conf.read(_resolve_conf_name(conf_type))
    return conf.get(group, field)


def cs(group, field, value, conf_type='global'):
    raise NotImplementedError('Use config.get_config([config_type]) and .setoption method')
    """Set configuration value"""
    conf = ConfigParser.RawConfigParser()
    fnm = _resolve_conf_name(conf_type)
    conf.read(fnm)
    conf.set(group, field, value)
    with open(fnm, 'wb') as configfile:
        conf.write(configfile)


def clist(group, conf_type='global'):
    raise NotImplementedError('Use config.get_config([config_type]) and .getlist method')
    """List configuration values"""
    conf = ConfigParser.RawConfigParser()
    conf.read(_resolve_conf_name(conf_type))
    return conf.items(group)


def has_option(group, field, conf_type='global'):
    raise NotImplementedError('Use config.get_config([config_type]) and .has_option method')
    """Return whether an option is available for that section"""
    conf = ConfigParser.RawConfigParser()
    conf.read(_resolve_conf_name(conf_type))
    return conf.has_option(group, field)
