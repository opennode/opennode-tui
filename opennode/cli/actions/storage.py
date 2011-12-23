
import os
import re

from opennode.cli.config import c, cs
from opennode.cli.actions.utils import del_folder, execute, mkdir_p


__all__ = ['list_pools', 'set_default_pool', 'prepare_storage_pool']


def list_pools():
    """List existing storage pools"""
    pool_params = []
    try:
        pools = execute("virsh 'pool-list' | tail -n+3 |head -n-1").splitlines()
        for p in pools:
            p = re.sub("\s+" , " ", p.strip())
            pool_params.append(p.split(' '))
    except Exception, e:
        print "Unable to list storage pools: %s" %e
    return pool_params

def set_default_pool(name):
    """Set default storage pool"""
    cs('general', 'default-storage-pool', name)

def get_default_pool():
    """Return name of the storage pool to use by default. Or None if not configured"""
    name = c('general', 'default-storage-pool')
    return None if name is None or name == '' or name == 'None' else name

def delete_pool(pool_name):
    """Delete a storage pool"""
    try:
        execute("virsh 'pool-destroy %s'" %pool_name)
        execute("virsh 'pool-undefine %s'" %pool_name)
        del_folder(os.path.join(c('general', 'storage-endpoint'), pool_name))
        if pool_name == c('general', 'default-storage-pool'):
            set_default_pool('')
    except Exception, e:
        print "Failed to delete pool %s: %s" % (pool_name, e)
        
def add_pool(pool_name, careful=True):
    """Add a new pool_name"""
    if careful and filter(lambda p: p[0] == pool_name, list_pools()):
        print "Pool '%s' already exists." %pool_name
        return
    try:
        pool_name = re.sub(" " , "_", pool_name) # safety measure
        pool_path = os.path.join(c('general', 'storage-endpoint'), pool_name)
        mkdir_p(pool_path)
        prepare_storage_pool(pool_name)
        execute("virsh 'pool-define-as %s dir --target %s'" %(pool_name, pool_path))
        execute("virsh 'pool-start %s'" %pool_name)
        execute("virsh 'pool-autostart %s'" %pool_name)
    except Exception, e:
        print "Failed to create a new pool: %s" %e
        
def prepare_storage_pool(storage_pool=get_default_pool()):
    """Assures that storage pool has the correct folder structure"""
    # create structure
    storage_pool = "%s/%s" % (c('general', 'storage-endpoint'), storage_pool)
    mkdir_p("%s/iso/" % storage_pool)
    mkdir_p("%s/images/" % storage_pool)
    mkdir_p("%s/openvz/unpacked" % storage_pool)
    mkdir_p("%s/kvm/unpacked" % storage_pool)
        