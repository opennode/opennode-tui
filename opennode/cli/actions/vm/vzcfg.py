""" Creates OpenVz container configuration """

# Defaults
DEF_CPUUNITS    = 1000        # Default CPU priority
DEF_INODES      = 200000      # Default nr. of filesystem inodes per 1GB
DEF_QUOTATIME   = 1800        # Default quota burst time 

def get_config(user_settings):
    """Output OpenVZ configuration file"""
    
    return template % {
        "physpages_barrier": user_settings["memory"],
        "physpages_limit": user_settings["memory"],
        "swappages_barrier": user_settings["memory"],
        "swappages_limit": user_settings["memory"],
        
        "diskspace_soft": user_settings["disk"],
        "diskspace_hard": float(user_settings["disk"]) + 1,
        "diskinodes_soft": round(float(user_settings["disk"]) * DEF_INODES),
        "diskinodes_hard": round(float(user_settings["disk"]) * DEF_INODES * 1.10),
        "quotatime": DEF_QUOTATIME,
        
        "cpus": user_settings["vcpu"],
        "cpulimit": float(user_settings["vcpulimit"]) * int(user_settings["vcpu"]),
        'cpuunits': DEF_CPUUNITS
    }

template = """\
# UBC parameters (in form of barrier:limit)
PHYSPAGES="%(physpages_barrier)sG:%(physpages_limit)sG"
SWAPPAGES="%(swappages_barrier)sG:%(swappages_limit)sG"
KMEMSIZE="unlimited"
LOCKEDPAGES="unlimited"
PRIVVMPAGES="unlimited"
SHMPAGES="unlimited"
NUMPROC="unlimited"
VMGUARPAGES="unlimited"
OOMGUARPAGES="unlimited"
NUMTCPSOCK="unlimited"
NUMFLOCK="unlimited"
NUMPTY="unlimited"
NUMSIGINFO="unlimited"
TCPSNDBUF="unlimited"
TCPRCVBUF="unlimited"
OTHERSOCKBUF="unlimited"
DGRAMRCVBUF="unlimited"
NUMOTHERSOCK="unlimited"
DCACHESIZE="unlimited"
NUMFILE="unlimited"
NUMIPTENT="unlimited"

# Disk quota parameters (in form of softlimit:hardlimit)
DISKSPACE="%(diskspace_soft)sG:%(diskspace_hard)sG"
DISKINODES="%(diskinodes_soft)s:%(diskinodes_hard)s"
QUOTATIME="%(quotatime)s"

# CPU fair scheduler parameter
CPUUNITS="%(cpuunits)s"
CPULIMIT="%(cpulimit)s"
CPUS="%(cpus)s"
"""
