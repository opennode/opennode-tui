import os

def list_bridges():
    """Returns a list of existing bridge interfaces"""
    return [x.strip() for x in os.popen('brctl show | awk \'NR>1{print $1}\'')]

def add_bridge(bridge):
    """Create a new bridge with default parameters"""
    os.command('brctl addbr %s' % bridge)

def configure_bridge(bridge, hello=None, fd=None, stp=None):
    """Set bridge parameters."""
    if hello is not None:
        os.command('brctl sethello %s %d' % (bridge, hello))
    if fd is not None:
        os.command('brctl setfd %s %d' % (bridge, fd))
    if stp is not None:
        os.command('brctl stp %s %s' % (bridge, stp))

def add_nameserver(ns):
    """Append a nameserver entry to the configuration"""
    with open('/etc/resolv.conf', 'a') as dnsservers:
        dnsservers.write('nameserver %s' % ns)
        


