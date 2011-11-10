from func.minion.modules import func_module
import os
import netifaces

class Host(func_module.FuncModule):
    version = "0.0.1"
    api_version = "0.0.1"
    description = "opennode host module"


    def interfaces(self):
        def number_of_set_bits(x):
            x -= (x >> 1) & 0x55555555
            x = ((x >> 2) & 0x33333333) + (x & 0x33333333)
            x = ((x >> 4) + x) & 0x0f0f0f0f
            x += x >> 8
            x += x >> 16
            return x & 0x0000003f

        def details(name):
            res = {'type': 'simple'}

            if os.path.exists('/sys/class/net/' + name + '/tun_flags'):
                res['type'] = 'virtual'

            sys_bridge_path = '/sys/class/net/' + name + '/brif/'
            if os.path.exists(sys_bridge_path):
                res['type'] = 'bridge'
                res['members'] = os.listdir(sys_bridge_path)

            addrs = netifaces.ifaddresses(name)
            res['mac'] = addrs[netifaces.AF_LINK][0]['addr']

            if addrs.has_key(netifaces.AF_INET):
                ip = addrs[netifaces.AF_INET][0]['addr']
                mask = addrs[netifaces.AF_INET][0]['netmask']

                l = 0
                for b in mask.split('.'):
                    l = l << 8 | int(b)
                prefix = number_of_set_bits(l)
                res['ip'] = '%s/%s' % (ip, prefix)

            return res

        return dict((i, details(i)) for i in netifaces.interfaces())
