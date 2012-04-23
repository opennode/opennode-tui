from func.minion.modules import func_module

import os
import netifaces

from func.minion import sub_process

from opennode.cli.actions.utils import execute
from opennode.cli import config


class Host(func_module.FuncModule):
    version = "0.0.1"
    api_version = "0.0.1"
    description = "opennode host module"

    def uptime(self):
        return execute("awk '{print $1}' /proc/uptime")

    def interfaces(self):
        def number_of_set_bits(x):
            x -= (x >> 1) & 0x55555555
            x = ((x >> 2) & 0x33333333) + (x & 0x33333333)
            x = ((x >> 4) + x) & 0x0f0f0f0f
            x += x >> 8
            x += x >> 16
            return x & 0x0000003f

        def details(name):
            res = {'type': 'simple', 'name': name}

            if os.path.exists('/sys/class/net/' + name + '/tun_flags'):
                res['type'] = 'virtual'

            sys_bridge_path = '/sys/class/net/' + name + '/brif/'
            if os.path.exists(sys_bridge_path):
                res['type'] = 'bridge'
                res['members'] = os.listdir(sys_bridge_path)

            addrs = netifaces.ifaddresses(name)
            if addrs.has_key(netifaces.AF_LINK):
                res['mac'] = addrs[netifaces.AF_LINK][0]['addr']

            if addrs.has_key(netifaces.AF_INET):
                ip = addrs[netifaces.AF_INET][0]['addr']
                mask = addrs[netifaces.AF_INET][0]['netmask']

                l = 0
                for b in mask.split('.'):
                    l = l << 8 | int(b)
                prefix = number_of_set_bits(l)
                res['ip'] = '%s/%s' % (ip, prefix)

            default_name = config.c('general', 'main_iface') if config.has_option('general', 'main_iface') else 'vmbr0'
            if name == default_name:
                res['primary'] = True

            return res

        return [details(i) for i in netifaces.interfaces()]

    def disk_usage(self, partition=None):
        """
        Returns the results of df -PT
        """
        results = {}
        # splitting the command variable out into a list does not seem to function
        # in the tests I have run
        command = '/bin/df -lPT'
        if (partition):
            command += ' %s' % (partition)
        cmdref = sub_process.Popen(command, stdout=sub_process.PIPE,
                                   stderr=sub_process.PIPE, shell=True,
                                   close_fds=True)
        (stdout, stderr) = cmdref.communicate()

        for disk in stdout.split('\n'):
            if (disk.startswith('Filesystem') or not disk):
                continue
            (device, fstype, total, used, available, percentage, mount) = disk.split(None, 7)
            results[mount] = {'device':device,
                              'total':str(total),
                              'used':str(used),
                              'available':str(available),
                              'fstype':str(fstype),
                              'percentage':int(percentage[:-1])}
        return results
