from __future__ import absolute_import

from func.minion.modules import func_module
from func.minion.modules.onode.common import delegate_methods


class VM(func_module.FuncModule):
    version = "0.0.1"
    api_version = "0.0.1"
    description = "opennode vm module"

from opennode.cli.actions import vm as mod
delegate_methods(VM, mod)
