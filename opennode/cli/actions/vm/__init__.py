from opennode.cli.actions.vm import kvm, openvz

vm_types = {
    "openvz": openvz,
    "kvm": kvm,
}

def get_module(vm_type):
    try:
        return vm_types[vm_type]
    except KeyError:
        raise NotImplementedError, "Vm type '%s' is not (yet) supported" % vm_type
