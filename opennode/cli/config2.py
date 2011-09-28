import ConfigParser

GLOBAL_CONF_LOCATION = 'opennode-tui.conf' #'/etc/opennode/opennode-tui.conf'
OPENVZ_CONF_LOCATION = 'openvz-defaults.conf'
KVM_CONF_LOCATION    = 'kvm-defaults.conf'

class Config:
    
    def __init__(self, conf_location):
        self.conf_location = conf_location
        self.config = ConfigParser.RawConfigParser()
        self.config.read(conf_location)
    
    def c(self, group, field):
        """Shorthand for getting configuration values"""
        return self.config.get(group, field)
    
    def clist(self, group):
        """Shorthand for getting a list of all configuration values"""
        return self.config.items(group)
        
    def cs(self, group, field, value):
        """Shorthand for setting configuration values"""
        self.config.set(group, field, value)
        with open(self.conf_location, 'wb') as configfile:
            self.config.write(configfile)

global_config = Config(GLOBAL_CONF_LOCATION)
openvz_config = Config(OPENVZ_CONF_LOCATION)
kvm_config = Config(KVM_CONF_LOCATION)
