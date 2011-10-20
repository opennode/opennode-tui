from __future__ import absolute_import

from xml.etree import ElementTree

import libvirt
from certmaster.config import BaseConfig, ListOption
from func.minion.modules import func_module


_connections = {}


class VM(func_module.FuncModule):
    version = "0.0.1"
    api_version = "0.0.1"
    description = "opennode vm module"

    class Config(BaseConfig):
        backends = ListOption()

    def backends(self):
        return self.options.backends

    def connection(self, backend):
        if backend not in self.options.backends and not backend.startswith('test://'):
            raise Exception("unsupported backend")

        conn = libvirt.open(backend)
        if backend.startswith('test://'):
            dom = conn.lookupByName('vm1')
            dom.shutdown()

        return conn

    def dom_dom(self, backend, name):
        return ElementTree.fromstring(self.connection(backend).lookupByName(name).XMLDesc(0))

    def list_vm_ids(self, backend):
        conn = self.connection(backend)
        return map(str, conn.listDefinedDomains() + conn.listDomainsID())

    def list_vms(self, backend):
        conn = self.connection(backend)

        online =  [{"id":i, "name": conn.lookupByID(i).name(), "state": "active"} for i in conn.listDomainsID()]
        offline = [{"id":None, "name":i, "state": "inactive"} for i in conn.listDefinedDomains()]
        return online + offline

    def start_vm(self, backend, name):
        conn = self.connection(backend)
        dom = conn.lookupByName(name)
        dom.create()

    def shutdown_vm(self, backend, name):
        conn = self.connection(backend)
        dom = conn.lookupByName(name)
        dom.shutdown()

    def destroy_vm(self, backend, name):
        conn = self.connection(backend)
        dom = conn.lookupByName(name)
        dom.destroy()

    def reboot_vm(self, backend, name):
        conn = self.connection(backend)
        dom = conn.lookupByName(name)
        dom.reboot()

    def suspend_vm(self, backend, name):
        conn = self.connection(backend)
        dom = conn.lookupByName(name)
        dom.suspend()

    def resume_vm(self, backend, name):
        conn = self.connection(backend)
        dom = conn.lookupByName(name)
        dom.resume()

    def vm_console_vnc(self, backend, name):
        return dict(port=self.dom_dom(backend, name).find('.//graphics[@type="vnc"]').attrib['port'])

    def vm_console_pty(self, backend, name):
        return dict(pty=self.dom_dom(backend, name).find('.//console[@type="pty"]').attrib['tty'])


#delegate_methods(VM, mod)
