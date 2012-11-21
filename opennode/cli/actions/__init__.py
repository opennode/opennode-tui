import sys

from opennode.cli.actions import oms, console, host
from opennode.cli.actions import templates, storage
from opennode.cli.actions import vm, sysresources, network

def smolt_hardware_info():
    """ Get hardware information from smolt. """
    try:
        sys.path.append("/usr/share/smolt/client")
        import smolt
    except ImportError:
        return {'_error': 'smolt is not installed'}

    hardware = smolt.Hardware()

    return dict((param, str(getattr(hardware.host, param)))
                     for param in dir(hardware.host)
                     if not param.startswith('_') and getattr(hardware.host, param))

def hardware_info():
    data = {
        'os'              : sys.platform,
        'defaultRunlevel' : '5',
        'bogomips'        : 'Unknown',
        'cpuVendor'       : 'Unknown',
        'cpuModel'        : 'Unknown',
        'numCpus'         : 'Unknown',
        'cpuSpeed'        : 'Unknown',
        'systemMemory'    : 'Unknown',
        'systemSwap'      : 'Unknown',
        'kernelVersion'   : 'Unknown',
        'language'        : 'Unknown',
        'platform'        : sys.platform,
        'systemVendor'    : 'Unknown',
        'systemModel'     : 'Unknown',
        'formfactor'      : 'Unknown',
        'selinux_enabled' : 'Unknown',
        'selinux_enforce' : 'Unknown',
    }

    smolt_data = smolt_hardware_info()
    if not smolt_data.get('_error', None):
        data.update(smolt_data)
    return data


# Salt hack: make actions module flat
def _extract_callables(mod, package, level):
    for member in dir(mod):
        memberobj = getattr(mod, member)
        if not member.startswith('_') and callable(memberobj):
            flat_name = '{0}_{1}'.format(mod.__name__[len(package)+1:].replace('.', '_'), member)
            assert not flat_name.startswith('_'), (flat_name, 'from', mod.__name__, package, member)
            globals()[flat_name] = memberobj
        elif (type(memberobj) is type(oms)):
            if not memberobj.__package__ or (not memberobj.__package__.startswith(package)):
                # ignore modules that are not part of the same package
                continue
            _extract_callables(memberobj, package, level+1)


def _generate_classes():
    _canonical_name = 'opennode.cli.actions'
    for name, mod in globals().items():
        if type(mod) is not type(oms):
            continue
        if mod.__name__.startswith(_canonical_name):
            _extract_callables(mod, _canonical_name, 0)

_generate_classes()

__all__ = [oms, console, host, templates, storage, vm, sysresources, network, hardware_info]
