import re

from opennode.cli.utils import execute

__all__ = ['list_bridges', 'add_bridge', 'configure_bridge',
           'add_nameserver', 'remove_nameserver']


def list_bridges():
    """Returns a list of existing bridge interfaces"""
    return [x.strip() for x in execute('brctl show | awk \'NR>1{print $1}\'').split('\n')]

def add_bridge(bridge):
    """Create a new bridge with default parameters"""
    execute('brctl addbr %s' % bridge)
    # TODO register bridge with libvirt
    
def configure_bridge(bridge, hello=None, fd=None, stp=None):
    """Set bridge parameters."""
    if hello is not None:
        execute('brctl sethello %s %d' % (bridge, hello))
    if fd is not None:
        execute('brctl setfd %s %d' % (bridge, fd))
    if stp is not None:
        execute('brctl stp %s %s' % (bridge, stp))

def add_nameserver(ns):
    """Append a nameserver entry to /etc/resolv.conf"""
    with open('/etc/resolv.conf', 'r+') as dnsservers:
        entries = dnsservers.readlines()
        for entry in entries:
            if re.match("\s*nameserver\s+%s\s*\n?$" %ns, entry) is not None:
                return # already exists
        entries.append('nameserver %s\n' % ns)
        dnsservers.seek(0)
        dnsservers.writelines(entries)

def remove_nameserver(ns):
    """Remove nameserver entry from /etc/resolv.conf"""
    filtered_entries = []
    with open('/etc/resolv.conf', 'r') as dnsservers:
        entries = dnsservers.readlines()
        for entry in entries:
            if re.match("\s*nameserver\s+%s\s*\n?$" %ns, entry) is not None:
                continue
            filtered_entries.append(entry)
    with open('/tmp/resolv.conf', 'w') as dnsservers:
        dnsservers.writelines(filtered_entries)

