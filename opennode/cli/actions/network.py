import re
import socket

from opennode.cli.actions.utils import execute


__all__ = ['list_bridges', 'add_bridge', 'configure_bridge', 'delete_bridge',
           'add_nameserver', 'remove_nameserver', 'add_bridge_interface',
           'remove_bridge_interface', 'list_bridge_interface',
           'show_routing_table', 'validate_server_addr', 'list_nameservers']


def list_bridges():
    """Returns a list of existing bridge interfaces or None if none defined"""
    bridges = [x.strip() for x in \
               execute('brctl show | awk \'NR>1{print $1}\'').splitlines()]
    return None if len(bridges) == 0 else bridges


def add_bridge(bridge):
    """Create a new bridge with default parameters"""
    execute('brctl addbr %s' % bridge)


def delete_bridge(bridge):
    """Delete network bridge and unregister from libvirt"""
    execute('brctl delbr %s' % bridge)


def configure_bridge(bridge, hello=None, fd=None, stp=None):
    """Set bridge parameters."""
    if hello is not None:
        execute('brctl sethello %s %d' % (bridge, hello))
    if fd is not None:
        execute('brctl setfd %s %d' % (bridge, fd))
    if stp is not None:
        execute('brctl stp %s %s' % (bridge, stp))


def add_bridge_interface(bridge, interface):
    """Add network interface to a bridge"""
    execute('brctl addif %s %s' % (bridge, interface))


def remove_bridge_interface(bridge, interface):
    """Remove network interface from a bridge"""
    execute('brctl delif %s %s' % (bridge, interface))


def list_bridge_interface(bridge):
    execute("brctl show | tail -n+2 | awk '{print $4}'")


def list_nameservers():
    """Append a nameserver entry to /etc/resolv.conf"""
    with open('/etc/resolv.conf', 'r') as dnsservers:
        entries = dnsservers.readlines()
        dns = []
        for entry in entries:
            if re.match("\s*nameserver", entry) is not None:
                dns.append(entry.split()[1])
        return dns


def add_nameserver(ns):
    """Append a nameserver entry to /etc/resolv.conf"""
    with open('/etc/resolv.conf', 'r+') as dnsservers:
        entries = dnsservers.readlines()
        for entry in entries:
            if re.match("\s*nameserver\s+%s\s*\n?$" % ns, entry) is not None:
                return  # already exists
        entries.append('nameserver %s\n' % ns)
        dnsservers.seek(0)
        dnsservers.writelines(entries)


def remove_nameserver(ns):
    """Remove nameserver entry from /etc/resolv.conf"""
    filtered_entries = []
    with open('/etc/resolv.conf', 'r') as dnsservers:
        entries = dnsservers.readlines()
        for entry in entries:
            if re.match("\s*nameserver\s+%s\s*\n?$" % ns, entry) is not None:
                continue
            filtered_entries.append(entry)
    with open('/tmp/resolv.conf', 'w') as dnsservers:
        dnsservers.writelines(filtered_entries)


def show_routing_table(*args):
    """Get server's routing table entries.
    It's different from the bundled func net module's method because
    it doesn't attempt to resolve the hostname of the ip addresses.
    """

    output = execute("route -n")
    lines = output.split("\n")
    lines = lines[2:]
    route_list = []
    for line in lines:
        route_dict = dict()
        line = line.split()
        route_dict["destination"] = line[0]
        route_dict["router"] = line[1]
        route_dict["netmask"] = line[2]
        route_dict["flags"] = line[3]
        route_dict["metrics"] = line[4]
        route_dict["count"] = line[5]
        route_dict["use"] = line[6]
        route_dict["interface"] = line[7]
        route_list.append(route_dict)
    return route_list


def validate_server_addr(server, port):
    """Validate server name and port of the OMS server. Return True/False"""
    # make sure that we can find at least one way of connecting to the system
    try:
        return len(socket.getaddrinfo(server, port)) > 1
    except socket.gaierror:
        return False
