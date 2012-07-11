import unittest

from opennode.cli.actions import templates


class TestTemplates(unittest.TestCase):

    def setUp(self):
        pass

    def test_get_template_repos(self):
        expected_output = [('Default KVM images (kvm)', 'default-kvm-repo'),
                           ('Default OpenVZ images (openvz)', 'default-openvz-repo')]
        result = templates.get_template_repos()
        self.assertTrue(result == expected_output)

    def test_delete_template(self):
        # 1. Delete existing template 
        # 2. Delete unpacked files
        # 3. Fail for non-existing templates
        self.assertRaises(IOError, templates.delete_template('aa', 'aa', 'aa'))
        

if __name__ == '__main__':
    unittest.main()
