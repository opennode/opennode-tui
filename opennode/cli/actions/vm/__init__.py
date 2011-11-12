from opennode.cli.actions.vm import openvz, kvm


__all__ = ['get_module']


vm_types = {
    "openvz": openvz,
    "kvm": kvm, 
}

def get_module(vm_type):
    try:
        return vm_types[vm_type]
    except KeyError: 
        raise NotImplementedError, "Vm type '%s' not (yet) supported" % vm_type
