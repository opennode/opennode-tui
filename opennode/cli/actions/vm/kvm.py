# TODO: implement me
import libvirt


def get_adjusted_ovf_settings(ovf_filename):
    raise NotImplementedError
    
def validate_template_settings(template_settings, input_settings):
    raise NotImplementedError

def get_available_instances():
    """Return a list of defined KVM VMs"""
    conn = libvirt.open("qemu:///system")
    name_list = conn.listDefinedDomains();
    vm_dict = dict()
    for name in name_list:
        vm_dict[name] = name
    return vm_dict

def get_template_name(uid):
    """Return a name of the template used for creating specified VM."""
    raise NotImplementedError