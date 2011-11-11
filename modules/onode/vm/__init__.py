from __future__ import absolute_import

import os
import urlparse
import time
from functools import wraps
from uuid import UUID
from xml.etree import ElementTree

import libvirt
from certmaster.config import BaseConfig, ListOption
from func.minion.modules import func_module


_connections = {}


def vm_method(fun):
    @wraps(fun)
    def wrapper(self, backend, *args, **kwargs):
        conn = self._connection(backend)

        try:
            return fun(self, conn, *args, **kwargs)
        finally:
            if backend.startswith('test://') and backend != "test:///default":
                self._dump_state(conn, '/tmp/func_vm_test_state.xml')

    return wrapper


class VM(func_module.FuncModule):
    version = "0.0.1"
    api_version = "0.0.1"
    description = "opennode vm module"

    class Config(BaseConfig):
        backends = ListOption()

    def backends(self):
        return self.options.backends

    def _connection(self, backend):
        if backend not in self.options.backends and not backend.startswith('test://'):
            raise Exception("unsupported backend %s" % backend)

        conn = libvirt.open(backend)

        # implement the 'status="inactive"' exension in the test:/// xml dump
        # so that we can test more complex scenarios.
        if backend.startswith('test://') and backend != "test:///default":
            path = urlparse.urlparse(backend).path
            conf = ElementTree.parse(path)

            for node in conf.findall('//domain'):
                if node.attrib.get('state', None) == 'inactive':
                    dom = conn.lookupByName(node.findtext('.//name'))
                    dom.shutdown()

        return conn

    def _dump_state(self, conn, filename):
        with open(filename, 'w') as f:
            os.chmod(filename, 0666)
            print >>f, '<?xml version="1.0"?>\n<node>'
            vms = self._list_vms(conn)
            for vm in vms:
                xml = conn.lookupByName(vm['name']).XMLDesc(0)
                node = ElementTree.fromstring(xml)
                node.attrib['state'] = vm['state']

                print >>f, ElementTree.tostring(node)
            print >>f, '</node>'

    def dom_dom(self, conn, uuid):
        return ElementTree.fromstring(conn.lookupByUUIDString(uuid).XMLDesc(0))

    def list_vm_ids(self, backend):
        conn = self.connection(backend)
        return map(str, conn.listDefinedDomains() + conn.listDomainsID())

    def _render_vm(self, conn, vm):
        def get_uuid(vm):
            return str(UUID(bytes=vm.UUID()))

        STATE_MAP = {
           0 : "active",
           1 : "active",
           2 : "active",
           3 : "suspended",
           4 : "inactive",
           5 : "inactive",
           6 : "inactive"
        }

        RUN_STATE_MAP = {
           0 : "no_state",
           1 : "running",
           2 : "blocked",
           3 : "suspended",
           4 : "shutting_down",
           5 : "shutoff",
           6 : "crashed"
        }

        info = vm.info()
        return {"uuid": get_uuid(vm), "name": vm.name(), "state": STATE_MAP[info[0]], "run_state": RUN_STATE_MAP[info[0]],
                'consoles': [i for i in [self._vm_console_vnc(conn, get_uuid(vm)), self._vm_console_pty(conn, get_uuid(vm))] if i],
                'interfaces': self._vm_interfaces(conn, get_uuid(vm))}

    def _list_vms(self, conn):
        online =  [self._render_vm(conn, vm) for vm in (conn.lookupByID(i) for i in conn.listDomainsID())]
        offline = [self._render_vm(conn, vm) for vm in (conn.lookupByName(i) for i in conn.listDefinedDomains())]
        return online + offline


    def free_mem(self):
        """Taken from func's Virt module,
        and adapted to handle multiple backends.

        The free memory is a concept which goes accross multiple virtualization
        backends, so it's the only method which doesn't require a specific backend parameter.

        """
        backends = self.backends()

        # Start with the physical memory and subtract
        memory = self._connection(backends[0]).getInfo()[1]

        # Take 256M off which is reserved for Domain-0
        memory = memory - 256

        for conn in (self._connection(b) for b in backends):
            for vm in (conn.lookupByID(i) for i in conn.listDomainsID()):
                # Exclude stopped vms and Domain-0 by using
                # ids greater than 0
                # NOTE: is this needed ? Seems that with kvm and lxc dom-0 is not reported
                if vm.ID() > 0:
                    # This node is active - remove its memory (in bytes)
                    memory = memory - int(vm.info()[2])/1024

        return memory

    @vm_method
    def list_vms(self, conn):
        return self._list_vms(conn)

    @vm_method
    def info_vm(self, conn, uuid):
        dom = conn.lookupByUUIDString(uuid)
        return self._render_vm(dom)

    @vm_method
    def start_vm(self, conn, uuid):
        dom = conn.lookupByUUIDString(uuid)
        dom.create()

    @vm_method
    def shutdown_vm(self, conn, uuid):
        dom = conn.lookupByUUIDString(uuid)
        dom.shutdown()

    @vm_method
    def destroy_vm(self, conn, uuid):
        dom = conn.lookupByUUIDString(uuid)
        dom.destroy()

    @vm_method
    def reboot_vm(self, conn, uuid):
        dom = conn.lookupByUUIDString(uuid)
        try:
            dom.reboot(0)
        except libvirt.libvirtError as e:
            if e.get_error_code() == libvirt.VIR_ERR_NO_SUPPORT:
                dom.shutdown()
                while True:
                    try:
                        if dom.info()[0] == 5:
                            break
                        time.sleep(1)
                    except libvirt.libvirtError as e:
                        # see opennode-management #34, or
                        # https://bugzilla.redhat.com/show_bug.cgi?id=519667
                        if e.get_error_domain() == libvirt.VIR_FROM_QEMU and e.get_error_code() == libvirt.VIR_ERR_OPERATION_FAILED:
                            continue
                        raise e
                dom.create()

    @vm_method
    def suspend_vm(self, conn, uuid):
        dom = conn.lookupByUUIDString(uuid)
        dom.suspend()

    @vm_method
    def resume_vm(self, conn, uuid):
        dom = conn.lookupByUUIDString(uuid)
        dom.resume()

    def _vm_console_vnc(self, conn, uuid):
        # python 2.6 etree library doesn't support xpath with predicate
        element = ([i for i in self.dom_dom(conn, uuid).findall('.//graphics') if i.attrib.get('type', None) == 'vnc'] or [None])[0]
        # elementtree element without children is treated as false
        if element != None:
            port = element.attrib.get('port', None)
            if port and port != '-1':
                return dict(type='vnc', port=port)

    vm_console_vnc = vm_method(_vm_console_vnc)

    def _vm_console_pty(self, conn, uuid):
        # python 2.6 etree library doesn't support xpath with predicate
        element = ([i for i in self.dom_dom(conn, uuid).findall('.//graphics') if i.attrib.get('type', None) == 'pty'] or [None])[0]
        if element != None:
            pty = element.attrib.get('tty', None)
            if pty:
                return dict(type='pty', pty=pty)

    vm_console_pty = vm_method(_vm_console_pty)

    def _vm_interfaces(self, conn, uuid):
        elements = self.dom_dom(conn, uuid).findall('.//interface')
        def interface(idx, i):
            type =  i.attrib.get('type')
            if type == 'network' and (i.find('forward') == None or i.find('forward').attrib.get('mode', None) == 'nat'):
                type = 'nat'

            mac = i.find('mac').attrib.get('address', None)

            alias = i.find('alias')
            if alias == None:
                alias = 'eth%s' % idx
            else:
                alias = alias.attrib.get('name', None)

            return dict(mac=mac, name=alias, type=type)

        return [interface(idx, i) for idx, i in enumerate(elements)]

    vm_interfaces = vm_method(_vm_interfaces)


#delegate_methods(VM, mod)
