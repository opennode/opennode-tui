import ConfigParser

config = ConfigParser.RawConfigParser()

CONF_LOCATION = 'opennode-tui.conf' #'/etc/opennode/opennode-tui.conf'

config.read(CONF_LOCATION)

def c(group, field):
    """Shorthand for getting configuration values"""
    return config.get(group, field)

