import os
import threading

from opennode.cli.actions import templates
from opennode.cli.actions import storage

from opennode.cli.tests import BaseTestCase, signal_when_called


class TestTemplates(BaseTestCase):

    def _setUp(self):
        self.testsp = 'testing'
        storage.add_pool(self.testsp)

    def _tearDown(self):
        try:
            storage.delete_pool(self.testsp)
        except Exception:
            pass

    def test_get_template_repos(self):
        expected_output = [('Default KVM images (kvm)', 'default-kvm-repo'),
                           ('Default OpenVZ images (openvz)', 'default-openvz-repo')]
        result = templates.get_template_repos()
        self.assertTrue(result == expected_output)

    def test_delete_nonexisting_template(self):
        self.assertRaises(IOError, templates.delete_template, self.testsp, 'gibberish', 'gibberish')

    def test_template_download(self):
        repos = templates.get_template_repos()
        repo_ids = map(lambda r: r[1], repos)
        remote_repo = 'default-openvz-repo'
        self.assertTrue(remote_repo in repo_ids)

        template_list = templates.get_template_list(remote_repo)
        template = template_list[0]

        local_templates = templates.get_local_templates('openvz', self.testsp)

        self.assertEqual(0, len(local_templates))

        self._addCleanup(templates.delete_template, self.testsp, 'openvz', template)

        templates.sync_template(remote_repo, template, self.testsp, silent=True)

        local_templates = templates.get_local_templates('openvz', self.testsp)
        self.assertTrue(len(local_templates) > 0)
        self.assertTrue(template in local_templates)

        expected_path = '/storage/%s/openvz/unpacked/%s.ovf' % (self.testsp, template)
        self.assertTrue(os.path.exists(expected_path), expected_path)

    def test_template_unavailable_while_downloaded(self):
        remote_repo = 'default-openvz-repo'
        template_list = templates.get_template_list(remote_repo)
        template = template_list[0]

        good_to_go = threading.Event()

        def signalling_unpack_template(*args, **kwargs):
            good_to_go.set()

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
            local_templates = templates.get_local_templates('openvz', self.testsp)

            self.assertFalse(template in local_templates,
                             '%s found in %s' % (template, local_templates))

            expected_path = '/storage/%s/openvz/unpacked/%s.ovf' % (self.testsp, template)
            self.assertFalse(os.path.exists(expected_path), expected_path)
        finally:
            sync_thread.join()
