from func.minion.modules import func_module
import func.minion.modules.opennode
from func.minion.modules.opennode.common import delegate_methods

from opennode.cli.actions import vm as mod

from opennode.cli.actions.vm import openvz


class VM(func_module.FuncModule):
    version = "0.0.1"
    api_version = "0.0.1"
    description = "opennode vm module"

    def vm_types(self):
        return mod.vm_types.keys()

    def list_vm_ids(self):
        return.openvz._get_openvz_ct_id_list()

delegate_methods(VM, mod)
