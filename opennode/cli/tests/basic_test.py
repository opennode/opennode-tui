import unittest

from opennode.cli import actions


def validate_size_limits(value, low, high):
    assert (int(value) < high), '%s is suspiciously large' % (value)
    assert int(value) > low, '%s is suspiciously small' % (value)


class TestBasic(unittest.TestCase):
    """
    Test basic functionality: method availability, basic API conformance etc
    """

    def setUp(self):
        pass

    def test_hardware_info(self):
        hwinfo = actions.hardware_info()
        self.assertTrue(hwinfo is not None)
        required_keys = ('cpuModel', 'os', 'numCpus', 'systemMemory', 'systemSwap')

        for key in required_keys:
            assert key in hwinfo, '%s is not in hwinfo %s' % (key, hwinfo)

        validate_size_limits(hwinfo['systemMemory'], 255, 1024 * 1024)
        validate_size_limits(hwinfo['systemSwap'], 0, 1024 * 1024)

    def test_method_availability(self):
        required_method_list = [
            'vm_autodetected_backends',
            'vm_list_vms',
            'vm_start_vm',
            'vm_shutdown_vm',
            'vm_destroy_vm',
            'vm_reboot_vm',
            'vm_suspend_vm',
            'vm_resume_vm',
            'vm_deploy_vm',
            'vm_undeploy_vm',
            'vm_get_local_templates',
            'vm_metrics',
            'vm_update_vm',
            'vm_migrate',
            'vm_set_owner',
            'vm_get_owner',
            'vm_change_ctid',
            'vm_clone_vm',
            'host_uptime',
            'host_interfaces',
            'host_disk_usage',
            'host_metrics',
        ]

        for method in required_method_list:
            assert callable(getattr(actions, method, None)), '%s not found in actions' % method
