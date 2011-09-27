from opennode.cli.actions.vm import openvz


__all__ = ['get_instance']


vm_types = {
    "openvz": openvz.VM,
}

def get_instance(storage_pool, type, template):
    vm_class = vm_types[type]
    return vm_class(storage_pool, type, template)
