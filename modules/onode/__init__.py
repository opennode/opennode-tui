from func.minion.modules import func_module

import sys
import time

sys.path.append('/home/marko/Projects/opennode/opennode-tui')


class OpenNode(func_module.FuncModule):
    version = "0.0.1"
    api_version = "0.0.1"
    description = "opennode module"

    def metrics(self):
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
                return [int(v) for v in execute("grep eth0 /proc/net/dev | awk -F: '{print $2}' | awk '{print $1, $9}'").split(' ')]

            t2, (rx2, tx2) = time.time(), get_netstats()
            t1, rx1, tx1 = roll_data("/tmp/func-network-host", (t2, rx2, tx2), (0, 0, 0))

            window = t2 - t1
            return ((rx2 - rx1) / window, (tx2 - tx1) / window)

        def diskspace_usage():
            return float(execute("df -P |grep ' /$' | head -n 1 | awk '{print $3/1024}'"))

        return dict(cpu_usage=cpu_usage(),
                    load=load(),
                    memory_usage=memory_usage(),
                    network_usage=max(network_usage()),
                    diskspace_usage=diskspace_usage())
