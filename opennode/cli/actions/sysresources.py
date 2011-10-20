""" System hardware resources """

import commands
from opennode.cli.utils import execute

def get_cpu_count():
    output = execute("cat /proc/cpuinfo | grep processor")
    cpu_count = len(output.split("\n"))
    return cpu_count
    
def get_cpu_usage_limit():
    return 100 * get_cpu_count()

def get_ram_size_gb():
    cmd_list = ["cat /proc/meminfo | grep MemFree",
                "cat /proc/meminfo | grep Buffers",
                "cat /proc/meminfo | grep Cached"]
    memory = 0
    for cmd in cmd_list:
        output = execute(cmd)
        try:
            memory += int(output.split()[1])
        except ValueError, IndexError:
            raise Exception, "Unable to calculate OpenNode server memory size"
    return round(float(memory) / 1024 ** 2, 3)

def get_disc_space_gb():
    output = execute("df /vz")
    tmp_output = output.split("\n", 1)
    if len(tmp_output) != 2:
        raise Exception, "Unable to calculate disk space"
    df_list = tmp_output[1].split()
    disk_space = float(df_list[3]) 
    return round(disk_space / 1024 ** 2, 3)

def get_min_disc_space_gb(vm_id):
    output = execute("vzquota stat %s | grep 1k-blocks" % str(vm_id))
    vals = output.split()
    return round(float(vals[1]) / 1024 ** 2, 2)
