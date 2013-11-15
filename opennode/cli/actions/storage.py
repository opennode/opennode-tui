
import os
import re
from xml.dom.minidom import parseString

from opennode.cli.config import get_config
from opennode.cli.log import get_logger
from opennode.cli.actions.utils import del_folder, execute, mkdir_p, CommandException


__all__ = ['list_pools', 'set_default_pool', 'prepare_storage_pool',
           'get_pool_path']


def list_pools():
    """List existing storage pools"""
    pool_params = []
    try:
        pools = execute("virsh 'pool-list' | tail -n+3 |head -n-1 | egrep -v '^default-iso |^default '").splitlines()
        for p in pools:
            p = re.sub("\s+", " ", p.strip())
            pool_params.append(p.split(' '))
    except Exception, e:
        msg = "Unable to list storage pools: %s" % e
        get_logger().error(msg)
        print msg
    return pool_params


def is_default_pool_modified():
    """Check if there were any modifications done by a user to the default pool"""
    try:
        config = get_config()
        res = execute("virsh 'pool-dumpxml default'")
        defined_path = parseString(res).getElementsByTagName('path')[0].lastChild.nodeValue
        # XXX: This will remain as-is right now.
        current_path = os.path.join(config.getstring('general', 'storage-endpoint'),
                                    config.getstring('general', 'default-storage-pool'),
                                    'images')
        return str(defined_path) != current_path
    except CommandException:
        return False  # pool is undefined or we are not sure -> so, assume it's all good


def set_default_pool(name):
    """Set default storage pool"""
    config = get_config()
    if name == 'default':
        raise CommandException('Cannot set pool name to a reserved "default".')

    # clean up default pool
    if not is_default_pool_modified():
        for pool_name in ['default', 'default-iso']:
            try:
                execute("virsh 'pool-destroy %s'" % pool_name)
                execute("virsh 'pool-undefine %s'" % pool_name)
            except CommandException:
                pass  # it's ok for these commands to fail if the pool is undefined
        endpoint = config.getstring('general', 'storage-endpoint')
        # create default image pool
        paths = {'default': 'images',
                 'default-iso': 'iso'}
        if len(name.strip()) > 0:
            for default_pool_name, item_path in paths.items():
                execute("virsh 'pool-define-as --name %s --type dir --target %s/%s/%s'" % (default_pool_name,
                                                                                           endpoint, name, item_path))
                execute("virsh 'pool-autostart %s'" % default_pool_name)
                execute("virsh 'pool-build %s'" % default_pool_name)
                execute("virsh 'pool-start %s'" % default_pool_name)
    # finally set a pointer in the configuration file
    config.setvalue('general', 'default-storage-pool', name)


def get_default_pool():
    """Return name of the storage pool to use by default. Or None if not configured"""
    name = get_config().getstring('general', 'default-storage-pool')
    return None if name is None or name == '' or name == 'None' else name


def delete_pool(pool_name):
    """Delete a storage pool"""
    try:
        config = get_config()
        if get_pool_path(pool_name) == '/storage/local':
            raise Exception('/storage/local can not be deleted')
        execute("virsh 'pool-destroy %s'" % pool_name)
        execute("virsh 'pool-undefine %s'" % pool_name)
        del_folder(get_pool_path(pool_name))
        if pool_name == config.getstring('general', 'default-storage-pool'):
            set_default_pool('')
    except Exception, e:
        raise Exception("Failed to delete pool %s: %s" % (pool_name, e))


def add_pool(pool_name, careful=True):
    """Add a new pool_name"""
    if careful and filter(lambda p: p[0] == pool_name, list_pools()):
        msg = "Pool '%s' already exists." % pool_name
        get_logger().warn(msg)
        print msg
        return
    try:
        pool_name = re.sub(" ", "_", pool_name)  # safety measure
        pool_path = os.path.join(get_config().getstring('general', 'storage-endpoint'),
                                 pool_name)
        mkdir_p(pool_path)
        prepare_storage_pool(pool_name)
        execute("service libvirt start")
        execute("virsh 'pool-define-as %s dir --target %s'" % (pool_name, pool_path))
        execute("virsh 'pool-start %s'" % pool_name)
        execute("virsh 'pool-autostart %s'" % pool_name)
    except Exception, e:
        msg = "Failed to create a new pool: %s" % e
        get_logger().error(msg)
        print msg


def prepare_storage_pool(storage_pool=get_default_pool()):
    """Assures that storage pool has the correct folder structure"""
    # create structure
    storage_pool = "%s/%s" % (get_config().getstring('general', 'storage-endpoint'),
                              storage_pool)
    mkdir_p("%s/iso/" % storage_pool)
    mkdir_p("%s/images/" % storage_pool)
    mkdir_p("%s/openvz/unpacked" % storage_pool)
    mkdir_p("%s/kvm/unpacked" % storage_pool)


def get_pool_path(storage_pool):
    return parseString(execute("virsh 'pool-dumpxml %s'" % storage_pool)).\
        getElementsByTagName('path')[0].lastChild.nodeValue
