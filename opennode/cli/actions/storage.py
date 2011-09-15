
import os

from opennode.cli.config import c, cs

def list_pools():
    """List existing storage pools"""
    pools = []
    try:
        pools = os.listdir(c('general', 'storage-endpoint'))
    except OSError:
        print "%s is empty" % c('general', 'storage-endpoint')
        # incorrect folder in the configuration
        pass
    return pools

def set_default_pool(name):
    """Set default storage pool"""
    cs('general', 'default-storage-pool', name)

