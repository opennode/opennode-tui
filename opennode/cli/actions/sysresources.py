""" System hardware resources """

import commands

def get_cpu_count():
    (status, output) = commands.getstatusoutput("cat /proc/cpuinfo | grep processor")
    if status:
        raise Exception, "Unable to calculate OpenNode server CPU count"
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
        (status, output) = commands.getstatusoutput(cmd)
        if status:
            raise Exception, "Unable to calculate OpenNode server memory size: %s" % cmd
        try:
            memory += int(output.split()[1])
        except ValueError, IndexError:
            raise Exception, "Unable to calculate OpenNode server memory size"
    return round(float(memory) / 1024 ** 2, 3)

def get_disc_space_gb():
    (status, output) = commands.getstatusoutput("df /vz")
    if status:
        raise Exception, "Unable to calculate disk space"
    tmp_output = output.split("\n", 1)
    if len(tmp_output) != 2:
        raise Exception, "Unable to calculate disk space"
    df_list = tmp_output[1].split()
    disk_space = float(df_list[3]) 
    return round(disk_space / 1024 ** 2, 3)

def get_min_disc_space_gb(vm_id):
    (status, output) = commands.getstatusoutput(" vzquota stat %s |grep 1k-blocks" % str(vm_id))
    if status:
        raise Exception, "Unable to calculate disk space" 
    vals = output.split()
    return round(float(vals[1]) / 1024 ** 2, 2)
