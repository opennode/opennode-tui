from opennode.cli.actions.vm import kvm, openvz
from opennode.cli.ovfopenvz import OVF2Openvz


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
    deploy_converter = OVF2Openvz(vm_parameters['template_name'], vm_parameters['vm_name'])
    deploy_converter.unarchiveOVF()
    template_settings = deploy_converter.parseOVFXML()
    if logger:
        logger("Template settings %s" % (template_settings, ))

    deploy_converter.testSystem()

    template_errors = deploy_converter.updateOVFSettings(vm_parameters)
    if (len(template_errors) > 0):
        error_string = ""
        for (k, v) in template_errors.items():
            error_string = error_string + v + " "
            return error_string

    deploy_converter.prepareFileSystem()
    deploy_converter.generateOpenvzConfiguration()
    deploy_converter.writeOpenVZConfiguration()
    deploy_converter.defineOpenvzCT()
