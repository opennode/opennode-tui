from func.minion.modules import func_module

import sys

sys.path.append('/home/marko/Projects/opennode/opennode-tui')


class OpenNode(func_module.FuncModule):
    version = "0.0.1"
    api_version = "0.0.1"
    description = "opennode module"
