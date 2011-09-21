import string

from opennode.cli import constants

class VM:
    def __init__(self, storage_pool, type, template):
        self.storage_pool = storage_pool 
        self.type = type
        self.template = template
        
    def read_template_settings(self):
        """ Reads .ovf configuration file, returns a dictionary of settings. """
        # Stub implementation
        # TODO: implement me
        ovf_template_settings = dict()
        ovf_template_settings["vm_id"] = "0"
        ovf_template_settings["template_name"] = string.join(self.template, "")
        ovf_template_settings["vm_name"] = string.join(self.type, "")
        ovf_template_settings["domain_type"] = "openvz" 
        ovf_template_settings["memory"] = str(constants.OPENVZ_DEFAULT_MEMORY)
        ovf_template_settings["min_memory"] = str(constants.OPENVZ_DEFAULT_MEMORY)
        ovf_template_settings["max_memory"] = str(constants.OPENVZ_DEFAULT_MEMORY)
        ovf_template_settings["vcpu"] = str(constants.OPENVZ_DEFAULT_VCPU)
        ovf_template_settings["min_vcpu"] = str(constants.OPENVZ_DEFAULT_VCPU)
        ovf_template_settings["max_vcpu"] = str(constants.OPENVZ_DEFAULT_VCPU)
        ovf_template_settings["disk"] = str(constants.OPENVZ_DEFAULT_DISK)
        ovf_template_settings["min_disk"] = str(constants.OPENVZ_DEFAULT_DISK)
        ovf_template_settings["max_disk"] = str(constants.OPENVZ_DEFAULT_DISK)
        ovf_template_settings["vcpulimit"] = str(constants.OPENVZ_DEFAULT_VCPULIMIT)  
        ovf_template_settings["min_vcpulimit"] = str(constants.OPENVZ_DEFAULT_VCPULIMIT) 
        ovf_template_settings["max_vcpulimit"] = str(constants.OPENVZ_DEFAULT_VCPULIMIT)
        ovf_template_settings["ip_address"] = "192.168.0.1"
        ovf_template_settings["nameserver"] = "192.168.0.1"
        ovf_template_settings["passwd"] = ""
        return ovf_template_settings
