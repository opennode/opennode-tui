import unittest

from opennode.cli.actions import templates
from opennode.cli.actions import storage


class TestTemplates(unittest.TestCase):

    def setUp(self):
        self._cleanup = []
        self.testsp = 'testing-pool'
        storage.add_pool(self.testsp)

    def tearDown(self):
        for cleanupf, args, kwargs in self._cleanup:
            cleanupf(*args, **kwargs)

    def _addCleanup(self, f, *args, **kwargs):
        """ unittest2-inspired resource management """
        self._cleanup.append((f, args, kwargs))

    def test_get_template_repos(self):
        expected_output = [('Default KVM images (kvm)', 'default-kvm-repo'),
                           ('Default OpenVZ images (openvz)', 'default-openvz-repo')]
        result = templates.get_template_repos()
        self.assertTrue(result == expected_output)

    def test_delete_template(self):
        # 1. Delete existing template
        # 1.1. Download a template
        # 1.2. Delete the template
        # 2. Delete unpacked files
        # 3. Fail for non-existing templates
        self.assertRaises(IOError, templates.delete_template, self.testsp, 'gibberish', 'gibberish')

    def test_template_download(self):
        repos = templates.get_template_repos()
        repo_ids = map(lambda r: r[1], repos)
        assert 'default-openvz-repo' in repo_ids

        remote_repo = 'default-openvz-repo'
        template_list = templates.get_template_list(remote_repo)
        template = template_list[0]

        self._addCleanup(templates.delete_template, self.testsp, 'openvz', template)
        templates.sync_storage_pool(self.testsp, remote_repo, [template])

        local_templates = templates.get_local_templates('openvz', self.testsp)
        assert len(local_templates) > 0

