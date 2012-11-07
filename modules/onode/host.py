from func.minion.modules import func_module
from func.minion.modules.onode.common import delegate_methods

class Host(func_module.FuncModule):
    version = "0.0.1"
    api_version = "0.0.1"
    description = "opennode host module"

from opennode.cli.actions import host as mod
delegate_methods(Host, mod)
