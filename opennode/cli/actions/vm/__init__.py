import os

from ovf.OvfFile import OvfFile

from opennode.cli.actions.vm import kvm, openvz
from opennode.cli.config import c


vm_types = {
    "openvz": openvz,
    "kvm": kvm,
}

def get_module(vm_type):
    try:
        return vm_types[vm_type]
    except KeyError:
        raise NotImplementedError, "Vm type '%s' is not (yet) supported" % vm_type


def deploy_vm(vm_parameters, logger=None):
    from opennode.cli import actions

    storage_pool = actions.storage.get_default_pool()
    if storage_pool is None:
        raise  Exception("storage pool not defined")

    vm_type = vm_parameters['vm_type']

    template = vm_parameters['template_name']

    ovf_file = OvfFile(os.path.join(c("general", "storage-endpoint"),
                                    storage_pool, vm_type, "unpacked",
                                    template + ".ovf"))
    vm = actions.vm.get_module(vm_type)
    template_settings = vm.get_ovf_template_settings(ovf_file)

    template_settings.update(vm_parameters)

    errors = vm.adjust_setting_to_systems_resources(template_settings)
    if errors:
        logger("Got %s" % (errors,))
        raise  Exception("got errors %s" % (errors,))

    vm.deploy(template_settings, storage_pool)
