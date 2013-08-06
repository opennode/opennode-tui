import netifaces
import os
import subprocess
import time

from opennode.cli.actions.utils import execute
from opennode.cli.config import get_config


def uptime():
    return execute("awk '{print $1}' /proc/uptime")


def interfaces():
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

        config = get_config()
        default_name = (config.getstring('general', 'main_iface')
                        if config.has_option('general', 'main_iface') else 'vmbr0')
        if name == default_name:
            res['primary'] = True

        return res

    return [details(i) for i in netifaces.interfaces()]


def disk_usage(partition=None):
    """
    Returns the results of df -PT
    """
    results = {}
    # splitting the command variable out into a list does not seem to function
    # in the tests I have run
    command = '/bin/df -lPT'
    if (partition):
        command += ' %s' % (partition)

    cmdref = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              shell=True, close_fds=True)

    (stdout, stderr) = cmdref.communicate()

    for disk in stdout.split('\n'):
        if (disk.startswith('Filesystem') or not disk):
            continue
        (device, fstype, total, used, available, percentage, mount) = disk.split(None, 7)
        results[mount] = {'device': device,
                          'total': str(total),
                          'used': str(used),
                          'available': str(available),
                          'fstype': str(fstype),
                          'percentage': int(percentage[:-1])}
    return results


def metrics():
    from opennode.cli.actions.utils import execute, roll_data

    def cpu_usage():
        time_list_now = map(int, execute("head -n 1 /proc/stat").split(' ')[2:6])
        time_list_was = roll_data('/tmp/func-cpu-host', time_list_now, [0] * 6)
        deltas = [yi - xi for yi, xi in zip(time_list_now, time_list_was)]
        try:
            cpu_pct = 1 - (float(deltas[-1]) / sum(deltas))
        except ZeroDivisionError:
            cpu_pct = 0
        return cpu_pct

    def load():
        return float(execute("cat /proc/loadavg | awk '{print $1}'"))

    def memory_usage():
        return float(execute("free | tail -n 2 | head -n 1 |awk '{print $3 / 1024}'"))

    def network_usage():
        def get_netstats():
            iface = get_config().getstring('general', 'main_iface')
            return [int(v) for v in \
                    execute("grep %s: /proc/net/dev | awk -F: '{print $2}' | awk '{print $1, $9}'" % iface).split(' ')]
        try:
            t2, (rx2, tx2) = time.time(), get_netstats()
            t1, rx1, tx1 = roll_data("/tmp/func-network-host", (t2, rx2, tx2), (0, 0, 0))

            window = t2 - t1
            return ((rx2 - rx1) / window, (tx2 - tx1) / window)
        except ValueError:
            return (0, 0)  # better this way

    def diskspace_usage():
        return float(execute("df -P |grep ' /$' | head -n 1 | awk '{print $3/1024}'"))

    return dict(cpu_usage=cpu_usage(),
                load=load(),
                memory_usage=memory_usage(),
                network_usage=max(network_usage()),
                diskspace_usage=diskspace_usage())
