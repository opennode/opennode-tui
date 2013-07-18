import os
from uuid import uuid4

from opennode.cli.actions import templates
from opennode.cli.actions import storage
from opennode.cli.actions import vm

from opennode.cli.tests import BaseTestCase


class TestOpenVZ(BaseTestCase):

    def _setUp(self):
        self.testsp = 'local'
        storage.add_pool(self.testsp)

    def _tearDown(self):
        try:
            storage.delete_pool(self.testsp)
        except Exception:
            pass

    def test_deploy_vm(self):
        # 1. d/l template
        # 2. deploy a vm
        remote_repo = 'default-openvz-repo'
        template = templates.get_template_list(remote_repo)[0]

        self._addCleanup(templates.delete_template, self.testsp, 'openvz', template)
        templates.sync_template(remote_repo, template, self.testsp, silent=True)

        vmuuid = str(uuid4())
        vms = vm.list_vms('openvz:///system')
        assert vmuuid not in map(lambda v: v['uuid'], vms)

        self._addCleanup(vm.undeploy_vm, 'openvz:///system', vmuuid)

        vm.deploy_vm('openvz:///system',
                     {'passwd': 'test',
                      'template_name': template,
                      'owner': 'amikulin',
                      'start_vm': False,
                      'disk': 10.0,
                      'ip_address': '10.0.0.66',
                      'uuid': vmuuid,
                      'vm_type': 'openvz',
                      'nameservers': "[]",
                      'hostname': u'ft.openvz',
                      'vcpu': 1,
                      'swap': 0,
                      'autostart': False,
                      'memory': 1.0})

        vms = vm.list_vms('openvz:///system')

        expected_path = '/storage/%s/openvz/unpacked/%s.ovf' % (self.testsp, template)
        assert os.path.exists(expected_path), expected_path
        assert vmuuid in map(lambda v: v['uuid'], vms), "%s" % map(lambda v: v['uuid'], vms)
        nvm = filter(lambda v: v['uuid'] == vmuuid, vms)
        assert nvm[0]['vm_type'] == 'openvz'

    def test_deploy_vm_duplicate_uuid(self):
        # 1. d/l template
        # 2. deploy a vm
        remote_repo = 'default-openvz-repo'
        template = templates.get_template_list(remote_repo)[0]

        self._addCleanup(templates.delete_template, self.testsp, 'openvz', template)
        templates.sync_template(remote_repo, template, self.testsp, silent=True)

        vmuuid = str(uuid4())

        vms = vm.list_vms('openvz:///system')
        assert vmuuid not in map(lambda v: v['uuid'], vms), 'Unstable: %s is used already' % vmuuid

        self._addCleanup(vm.undeploy_vm, 'openvz:///system', vmuuid)

        vm.deploy_vm('openvz:///system',
                     {'passwd': 'test',
                      'template_name': template,
                      'owner': 'amikulin',
                      'start_vm': False,
                      'disk': 10.0,
                      'ip_address': '10.0.0.66',
                      'uuid': vmuuid,
                      'vm_type': 'openvz',
                      'nameservers': "[]",
                      'hostname': u'ft.openvz1',
                      'vcpu': 1,
                      'swap': 0,
                      'autostart': False,
                      'memory': 1.0})

        vms = vm.list_vms('openvz:///system')

        expected_path = '/storage/%s/openvz/unpacked/%s.ovf' % (self.testsp, template)
        self.assertTrue(os.path.exists(expected_path), expected_path)
        self.assertTrue(vmuuid in map(lambda v: v['uuid'], vms), "%s" % map(lambda v: v['uuid'], vms))
        nvm = filter(lambda v: v['uuid'] == vmuuid, vms)
        self.assertTrue(nvm[0]['vm_type'] == 'openvz')

        vm.deploy_vm('openvz:///system',
                     {'passwd': 'test',
                      'template_name': template,
                      'owner': 'amikulin',
                      'start_vm': False,
                      'disk': 10.0,
                      'ip_address': '10.0.0.66',
                      'uuid': vmuuid,
                      'vm_type': 'openvz',
                      'nameservers': "[]",
                      'hostname': u'ft.openvz2',
                      'vcpu': 1,
                      'swap': 0,
                      'autostart': False,
                      'memory': 1.0})

        vms = vm.list_vms('openvz:///system')
        nvm = filter(lambda v: v['uuid'] == vmuuid, vms)
        self.assertEquals(1, len(nvm))
