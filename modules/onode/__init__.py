from func.minion.modules import func_module
import sys

import opennode.cli.actions

sys.path.append('/home/marko/Projects/opennode/opennode-tui')


class OpenNode(func_module.FuncModule):
    version = "0.0.1"
    api_version = "0.0.1"
    description = "opennode module"

    def metrics(self):
        return opennode.cli.actions.metrics()
