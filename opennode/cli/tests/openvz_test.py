import os
import threading
from uuid import uuid4

from opennode.cli.actions import templates
from opennode.cli.actions import storage
from opennode.cli.actions import vm

from opennode.cli.tests import BaseTestCase, signal_when_called


class TestOpenVZ(BaseTestCase):

    def _setUp(self):
        self.testsp = 'local'
        storage.add_pool(self.testsp)
        self.typical_vm_params = {'passwd': 'test',
                                  'owner': 'amikulin',
                                  'start_vm': False,
                                  'disk': 10.0,
                                  'ip_address': '10.0.0.66',
                                  'vm_type': 'openvz',
                                  'nameservers': "[]",
                                  'hostname': u'ft.openvz',
                                  'vcpu': 1,
                                  'swap': 0,
                                  'autostart': False,
                                  'memory': 1.0}

    def _tearDown(self):
        try:
            storage.delete_pool(self.testsp)
        except Exception:
            pass

    def test_deploy_vm(self):
        remote_repo = 'default-openvz-repo'
        template = templates.get_template_list(remote_repo)[0]

        self._addCleanup(templates.delete_template, self.testsp, 'openvz', template)
        templates.sync_template(remote_repo, template, self.testsp, silent=True)

        vmuuid = str(uuid4())
        vms = vm.list_vms('openvz:///system')
        self.assertTrue(vmuuid not in map(lambda v: v['uuid'], vms))

        self._addCleanup(vm.undeploy_vm, 'openvz:///system', vmuuid)

        self.typical_vm_params.update({'uuid': vmuuid,
                                       'template_name': template})

        vm.deploy_vm('openvz:///system', self.typical_vm_params)

        vms = vm.list_vms('openvz:///system')

        expected_path = '/storage/%s/openvz/unpacked/%s.ovf' % (self.testsp, template)
        self.assertTrue(os.path.exists(expected_path), expected_path)
        self.assertTrue(vmuuid in map(lambda v: v['uuid'], vms),
                        "%s" % map(lambda v: v['uuid'], vms))
        nvm = filter(lambda v: v['uuid'] == vmuuid, vms)
        self.assertEqual(nvm[0]['vm_type'], 'openvz')

    def test_deploy_vm_duplicate_uuid(self):
        remote_repo = 'default-openvz-repo'
        template = templates.get_template_list(remote_repo)[0]

        self._addCleanup(templates.delete_template, self.testsp, 'openvz', template)
        templates.sync_template(remote_repo, template, self.testsp, silent=True)

        vmuuid = str(uuid4())

        vms = vm.list_vms('openvz:///system')
        self.assertTrue(vmuuid not in map(lambda v: v['uuid'], vms),
                        'Unstable: %s is used already' % vmuuid)

        self._addCleanup(vm.undeploy_vm, 'openvz:///system', vmuuid)

        self.typical_vm_params.update({'uuid': vmuuid,
                                       'template_name': template,
                                       'hostname': 'ft1.openvz'})

        vm.deploy_vm('openvz:///system', self.typical_vm_params)

        vms = vm.list_vms('openvz:///system')

        expected_path = '/storage/%s/openvz/unpacked/%s.ovf' % (self.testsp, template)
        self.assertTrue(os.path.exists(expected_path), expected_path)
        self.assertTrue(vmuuid in map(lambda v: v['uuid'], vms),
                        "%s" % map(lambda v: v['uuid'], vms))
        nvm = filter(lambda v: v['uuid'] == vmuuid, vms)
        self.assertTrue(nvm[0]['vm_type'] == 'openvz')

        self.typical_vm_params.update({'uuid': vmuuid,
                                       'template_name': template,
                                       'hostname': 'ft2.openvz'})

        vm.deploy_vm('openvz:///system', self.typical_vm_params)

        vms = vm.list_vms('openvz:///system')
        nvm = filter(lambda v: v['uuid'] == vmuuid, vms)
        self.assertEquals(1, len(nvm))

    def test_deploy_vm_while_template_is_downloaded(self):
        remote_repo = 'default-openvz-repo'
        template = templates.get_template_list(remote_repo)[0]

        good_to_go = threading.Event()

        try:
            orig_unpack_template = templates.unpack_template
            templates.unpack_template = signal_when_called(good_to_go)(templates.unpack_template)
            sync_thread = threading.Thread(name='sync_template_available_test',
                                           target=templates.sync_template,
                                           args=(remote_repo, template, self.testsp),
                                           kwargs={'silent': True})
            self._addCleanup(templates.delete_template, self.testsp, 'openvz', template)
            sync_thread.start()
            good_to_go.wait(240)
            self.assertTrue(good_to_go.is_set(), 'Timed out waiting for unpack_template to be invoked')
        finally:
            templates.unpack_template = orig_unpack_template

        try:
            vmuuid = str(uuid4())
            vms = vm.list_vms('openvz:///system')
            self._addCleanup(vm.undeploy_vm, 'openvz:///system', vmuuid)

            self.typical_vm_params.update({'uuid': vmuuid,
                                           'template_name': template,
                                           'hostname': 'ftdvwtd.openvz'})

            vm.deploy_vm('openvz:///system', self.typical_vm_params)

            vms = vm.list_vms('openvz:///system')

            self.assertFalse(vmuuid in map(lambda v: v['uuid'], vms),
                            "%s found in %s" % (vmuuid, map(lambda v: v['uuid'], vms)))

            expected_path = '/storage/%s/openvz/unpacked/%s.ovf' % (self.testsp, template)
            self.assertFalse(os.path.exists(expected_path), expected_path)
        finally:
            sync_thread.join()
