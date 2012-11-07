from func.minion.modules import func_module
from func.minion.modules.onode.common import delegate_methods


class Network(func_module.FuncModule):
    version = "0.0.1"
    api_version = "0.0.1"
    description = "opennode network module"


from opennode.cli.actions import network as mod
delegate_methods(Network, mod)
