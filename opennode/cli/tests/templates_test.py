import os

from opennode.cli.actions import templates
from opennode.cli.actions import storage

from opennode.cli.tests import BaseTestCase


class TestTemplates(BaseTestCase):

    def _setUp(self):
        self.testsp = 'testing'
        storage.add_pool(self.testsp)

    def _tearDown(self):
        try:
            storage.delete_pool(self.testsp)
            pass
        except Exception:
            pass

    def test_get_template_repos(self):
        expected_output = [('Default KVM images (kvm)', 'default-kvm-repo'),
                           ('Default OpenVZ images (openvz)', 'default-openvz-repo')]
        result = templates.get_template_repos()
        self.assertTrue(result == expected_output)

    def test_delete_template(self):
        # 1. Delete unpacked files
        # 2. Fail for non-existing templates
        self.assertRaises(IOError, templates.delete_template, self.testsp, 'gibberish', 'gibberish')

    def test_template_download(self):
        repos = templates.get_template_repos()
        repo_ids = map(lambda r: r[1], repos)
        remote_repo = 'default-openvz-repo'
        assert remote_repo in repo_ids

        template_list = templates.get_template_list(remote_repo)
        template = template_list[0]

        local_templates = templates.get_local_templates('openvz', self.testsp)

        assert len(local_templates) == 0

        self._addCleanup(templates.delete_template, self.testsp, 'openvz', template)

        templates.sync_template(remote_repo, template, self.testsp, silent=True)

        local_templates = templates.get_local_templates('openvz', self.testsp)
        assert len(local_templates) > 0
        assert template in local_templates

        expected_path = '/storage/%s/openvz/unpacked/%s.ovf' % (self.testsp, template)
        assert os.path.exists(expected_path), expected_path
