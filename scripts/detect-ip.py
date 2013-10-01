import guestfs
import re
import sys
import tempfile
import hivex
import os

def mount_roots(g, root):
    mps = g.inspect_get_mountpoints (root)
    def compare (a, b):
        if len(a[0]) > len(b[0]):
            return 1
        elif len(a[0]) == len(b[0]):
            return 0
        else:
            return -1
    mps.sort (compare)
    for mp_dev in mps:
        try:
            g.mount_ro (mp_dev[1], mp_dev[0])
        except RuntimeError as msg:
            print "%s (ignored)" % msg

def log_file(distro):
    if distro in ['fedora', 'rhel', 'redhat-based', 'centos']:
        return '/var/log/messages'
    if distro in ['ubuntu', 'debian']:
        return '/var/log/syslog'
    raise Exception("Don't know distro %s" % (distro))


def dhcp_address(g, root):
    guest_type = g.inspect_get_type(root);

    if guest_type == 'linux':
        return dhcp_address_linux(g, root, log_file(g.inspect_get_distro(root)))
    elif guest_type == 'windows':
        return dhcp_address_windows(g, root)
    else:
        raise Exception("Don't know OS %s" % guest_type)

def dhcp_address_linux(g, root, logfile):
    lines = g.egrep ("dhclient.*: bound to ", logfile);
    if not lines:
        raise Exception("Cannot find dhcp address")
    return re.match('.*bound to ([^ ]*).*', lines[-1]).group(1)


def dhcp_address_windows(g, root):
    system_path = g.case_sensitive_path('/windows/system32/config/system')
    if not system_path:
        raise Exception("cannot find HKLM\\\\System")

    tmpfile = None
    with tempfile.NamedTemporaryFile() as f:
        tmpfile = f.name

    try:
        g.download(system_path, tmpfile)

        h = hivex.Hivex(tmpfile)
        root = h.root()
        node = h.node_get_child(root, "Select")

        if node == 0:
            raise Exception("cannot find Select registry key")

        value = h.node_get_value(node, "Current")

        if value == 0:
            raise Exception("cannot find Select/Current registry value")

        controlset = 'ControlSet%03d' % h.value_dword(value)

        path = [controlset, "Services", "Tcpip", "Parameters", "Interfaces"]
        node = root
        for p in path:
            node = h.node_get_child(node, p)

        if node == 0:
            raise Exception("cannot find Interfaces registry key")

        nodes = h.node_children(node)

        for node in nodes:
            try:
                value = h.node_get_value(node, "DhcpIPAddress")
                if value:
                    return h.value_string(value)
            except:
                pass

    finally:
        os.remove(tmpfile)


if __name__ == '__main__':
    g = guestfs.GuestFS()
    g.add_drive_opts (sys.argv[1])
    g.launch ()

    roots = g.inspect_os ()

    if len(roots) > 1:
        raise Exception("cannot handle multiple OS images")

    root = roots[0]

    mount_roots(g, root)

    print dhcp_address(g, root)

    # Unmount everything.
    g.umount_all ()
