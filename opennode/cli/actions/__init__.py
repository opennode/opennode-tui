from opennode.cli.actions import oms, console, host, templates, storage, vm, sysresources, network


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
    import sys
    package = sys.modules[__name__].__package__
    for name, mod in globals().items():
        if type(mod) is not type(oms):
            continue
        if not mod.__package__.startswith(package):
            package = mod.__package__
        _extract_callables(mod, package, 0)

_generate_classes()
