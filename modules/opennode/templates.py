from func.minion.modules import func_module
import func.minion.modules.opennode
from func.minion.modules.opennode.common import delegate_methods

class Templates(func_module.FuncModule):
    version = "0.0.1"
    api_version = "0.0.1"
    description = "opennode templates module"


from opennode.cli.actions import templates as mod
delegate_methods(Templates, mod)
