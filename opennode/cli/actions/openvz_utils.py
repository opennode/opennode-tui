# -*- coding: utf-8 -*-

from opennode.cli.actions.utils import execute


def get_openvz_running_ctids():
    """
    Return a list of currently running OpenVZ CTs

    @return: List of OpenVZ containers on current machine
    @rtype: List
    """
    return map(int, [ctid for ctid in
                     execute('vzlist -H -o ctid').splitlines()
                     if 'Container' not in ctid])


def get_openvz_stopped_ctids():
    """
    Return a list of currently stopped OpenVZ CTs

    @return: List of OpenVZ containers on current machine
    @rtype: List
    """
    return map(int, [ctid for ctid in
                     execute('vzlist -S -H -o ctid').splitlines()])


def get_openvz_all_ctids():
    """
    Return a list of current OpenVZ CTs (both running and stopped)

    @return: List of OpenVZ containers on current machine
    @rtype: List
    """
    return map(int, [ctid for ctid in
                     execute('vzlist --all -H -o ctid').splitlines()])
