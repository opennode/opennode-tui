import cPickle as pickle
import os
import re
import shutil
import tarfile
import urlparse
import httplib

from ovf.OvfFile import OvfFile

from opennode.cli.config import get_config
from opennode.cli.actions import storage, vm as vm_ops
from opennode.cli.actions.utils import delete, calculate_hash, execute_in_screen, execute, download
from opennode.cli.actions.utils import urlopen, TemplateException
from opennode.cli.log import get_logger

__all__ = ['get_template_repos', 'get_template_list', 'sync_storage_pool', 'sync_template',
           'delete_template', 'unpack_template', 'get_local_templates', 'sync_oms_template', 'is_fresh',
           'is_syncing']


__context__ = {}


log = get_logger()


def _simple_download_hook(count, blockSize, totalSize):
    """Simple download counter"""
    log.info("% 3.1f%% of %d bytes\r" %
             (min(100, float(blockSize * count) / totalSize * 100), totalSize))


def get_template_repos():
    """Return a list of formatted strings describing configured repositories"""
    config = get_config()
    repo_groups = config.getstring('general', 'repo-groups').split(',')
    # XXX: Get autodetexted backends from config. If host has no kvm
    # capability then don't display KVM repo for template download.
    backends = config.getstring('general', 'backends').split(',')
    has_kvm = 'qemu:///system' in backends
    result = []
    for r in repo_groups:
        group = "%s-repo" % r.strip()
        name = config.getstring(group, 'name')
        vm_type = config.getstring(group, 'type')
        if not has_kvm and 'kvm' in vm_type:
            continue
        result.append(("%s (%s)" % (name, vm_type), group))
    return result


def get_template_list(remote_repo):
    """Retrieves a tmpl_list of templates from the specified repository"""
    url = get_config().getstring(remote_repo, 'url')
    url = url.rstrip('/') + '/'
    tmpl_list = urlopen(urlparse.urljoin(url, 'templatelist.txt'))
    templates = [template.strip() for template in tmpl_list]
    tmpl_list.close()
    return templates


def sync_storage_pool(storage_pool, remote_repo, templates,
                      sync_tasks_fnm=None, force=False, screen=True):
    """Synchronize selected storage pool with the remote repo. Only selected templates
    will be persisted, all of the other templates shall be purged.
    Ignores purely local templates - templates with no matching name in remote repo."""
    config = get_config()

    if not sync_tasks_fnm:
        sync_tasks_fnm = config.getstring('general', 'sync_task_list')

    vm_type = config.getstring(remote_repo, 'type')
    existing_templates = get_local_templates(vm_type, storage_pool)

    # synchronize selected templates
    if templates is None:
        templates = []

    purely_local_tmpl = get_purely_local_templates(storage_pool, vm_type, remote_repo)
    # might be not order preserving
    for_update = set(templates) - set(purely_local_tmpl)

    for_deletion = set(existing_templates) - for_update - set(templates)

    tasks = [(t, storage_pool, remote_repo) for t in for_update]

    # XXX at the moment only a single sync process is allowed.
    if os.path.exists(sync_tasks_fnm):
        if not force:
            raise TemplateException("Synchronization task pool already defined.")

    set_templates_sync_list(tasks, sync_tasks_fnm)

    # delete existing, but not selected templates
    for tmpl in for_deletion:
        delete_template(storage_pool, vm_type, tmpl)

    if screen:
        cli_command = "from opennode.cli.actions import templates;"
        cli_command += "templates.sync_templates_list('%s')" % sync_tasks_fnm
        execute_in_screen('OPENNODE-SYNC', 'python -c "%s"' % cli_command)
    else:
        sync_templates_list(sync_tasks_fnm)


def sync_template(remote_repo, template, storage_pool, silent=False):
    """Synchronizes local template (cache) with the remote one (master)"""
    config = get_config()
    url = config.getstring(remote_repo, 'url')
    vm_type = config.getstring(remote_repo, 'type')
    localfile = os.path.join(storage.get_pool_path(storage_pool), vm_type, template)
    remotefile = urlparse.urljoin(url.rstrip('/') + '/', template)

    # only download if we don't already have a fresh copy
    if is_fresh(localfile, remotefile):
        return

    extension = "ova" if _url_exists("%s.ova" % remotefile) else "tar"

    unfinished_local = "%s.%s.unfinished" % (localfile, extension)
    unfinished_local_hash = "%s.%s.pfff.unfinished" % (localfile, extension)

    remote_url = "%s.%s" % (remotefile, extension)

    if not _url_exists(remote_url):
        raise TemplateException("Remote template was not found: %s" % remote_url)

    retries = 5
    retry = 0
    while not is_fresh(localfile, remotefile, unfinished=True) and retries > retry:
        # for resilience
        retry += 1
        storage.prepare_storage_pool(storage_pool)
        download("%s.%s" % (remotefile, extension), unfinished_local, continue_=True, silent=silent)

        r_template_hash = "%s.%s.pfff" % (remotefile, extension)
        download(r_template_hash, unfinished_local_hash, continue_=True, silent=silent)

    os.rename(unfinished_local, '%s.%s' % (localfile, extension))
    os.rename(unfinished_local_hash, '%s.%s.pfff' % (localfile, extension))
    unpack_template(storage_pool, vm_type, localfile)


def import_template(template, vm_type, storage_pool=None):
    """Import external template into ON storage pool"""
    config = get_config()

    if not storage_pool:
        storage_pool = config.getstring('general', 'default-storage-pool')

    if not os.path.exists(template):
        raise RuntimeError("Template not found: %s" % template)

    if not (template.endswith('tar') or template.endswith('ova')):
        raise RuntimeError("Expecting a file ending with .tar or .ova for a template, %s" % template)

    tmpl_name = os.path.basename(template)
    target_file = os.path.join(storage.get_pool_path(storage_pool), vm_type, tmpl_name)

    log.info("Copying template to the storage pool... %s -> %s" % (template, target_file))
    shutil.copyfile(template, target_file)
    calculate_hash(target_file)

    log.info("Unpacking template %s..." % target_file)
    extension = 'ova' if template.endswith('ova') else 'tar'
    unpack_template(storage_pool, vm_type, tmpl_name.rstrip('.%s' % extension))


def delete_template(storage_pool, vm_type, template):
    """Deletes template, unpacked folder and a hash"""
    # get a list of files in the template
    config = get_config()
    log.info("Deleting %s (%s) from %s..." % (template, vm_type, storage_pool))
    storage_endpoint = config.getstring('general', 'storage-endpoint')
    templatefile = "%s/%s/%s/%s.tar" % (storage_endpoint, storage_pool, vm_type, template)
    if not os.path.exists(templatefile):
        templatefile = os.path.splitext(templatefile)[0] + '.ova'
    tmpl = tarfile.open(templatefile)
    for packed_file in tmpl.getnames():
        fnm = "%s/%s/%s/unpacked/%s" % (storage_endpoint, storage_pool, vm_type, packed_file)
        if not os.path.isdir(fnm):
            delete(fnm)
        else:
            shutil.rmtree(fnm)
    # remove master copy
    delete(templatefile)
    delete("%s.pfff" % templatefile)
    # also remove symlink for openvz vm_type
    if vm_type == 'openvz':
        delete("%s/%s" % (config.getstring('general', 'openvz-templates'), "%s.tar.gz" % template))


def unpack_template(storage_pool, vm_type, tmpl_name):
    """Unpacks template into the 'unpacked' folder of the storage pool.
       Adds symlinks as needed by the VM template vm_type."""
    # we assume location of the 'unpacked' to be the same as the location of the file
    basedir = os.path.join(storage.get_pool_path(storage_pool), vm_type)
    tar_name = ""
    if os.path.exists(os.path.join(basedir, "%s.tar" % tmpl_name)):
        tar_name = os.path.join(basedir, "%s.tar" % tmpl_name)
    if os.path.exists(os.path.join(basedir, "%s.ova" % tmpl_name)):
        tar_name = os.path.join(basedir, "%s.ova" % tmpl_name)
    tmpl = tarfile.open(tar_name)
    unpacked_dir = os.path.join(basedir, 'unpacked')
    tmpl.extractall(unpacked_dir)
    # special case for openvz vm_type
    if vm_type == 'openvz':
        from opennode.cli.actions import vm
        tmpl_name = [fnm for fnm in tmpl.getnames()
                     if fnm.endswith('tar.gz') and not fnm.endswith('scripts.tar.gz')]
        # make sure we have only a single tarball with the image
        assert len(tmpl_name) == 1
        vm.openvz.link_template(storage_pool, tmpl_name[0])


def get_local_templates(vm_type, storage_pool=None):
    """Returns a list of templates of a certain vm_type from the storage pool"""
    config = get_config()

    if not storage_pool:
        storage_pool = config.getstring('general', 'default-storage-pool')

    return [os.path.splitext(tmpl)[0] for tmpl in
            os.listdir("%s/%s" % (storage.get_pool_path(storage_pool), vm_type))
            if tmpl.endswith('tar') or tmpl.endswith('ova')]


def sync_oms_template(storage_pool=None):
    """Synchronize OMS template"""
    config = get_config()
    if not storage_pool:
        storage_pool = config.getstring('general', 'default-storage-pool')
    repo = config.getstring('opennode-oms-template', 'repo')
    tmpl = config.getstring('opennode-oms-template', 'template_name')
    sync_template(repo, tmpl, storage_pool)


def is_fresh(localfile, remotefile, unfinished=False):
    """Checks whether local copy matches remote file"""
    # get remote hash
    extension = "ova" if _url_exists("%s.ova" % remotefile) else "tar"
    remote_hashfile = urlopen("%s.%s.pfff" % (remotefile, extension))
    remote_hash = remote_hashfile.read()
    remote_hashfile.close()
    # get a local one
    try:
        with open("%s.%s.pfff%s" % (localfile, extension,
                                    '.unfinished' if unfinished else ''), 'r') as f:
            local_hash = f.read()
    except IOError:
        # no local hash found
        return False
    return remote_hash == local_hash


def list_templates():
    """ Prints all local and remote templates """
    # local templates
    config = get_config()
    for vm_type in ["openvz", "kvm"]:
        log.info("%s local templates:", vm_type.upper())
        for storage_pool in storage.list_pools():
            log.info("\t Storage: %s",
                     os.path.join(config.getstring("general", "storage-endpoint"),
                                  storage_pool[0], vm_type))
            for tmpl in get_local_templates(vm_type, storage_pool[0]):
                log.info("\t\t %s", tmpl)
            log.info('')
    # remote templates
    repo_groups = re.split(",\s*", config.getstring("general", "repo-groups"))
    repo_groups = [repo_group + "-repo" for repo_group in repo_groups]
    for repo_group in repo_groups:
        url, vm_type = config.getstring(repo_group, "url"), config.getstring(repo_group, "type")
        log.info("%s remote templates:", vm_type.upper())
        log.info("\t Repository: %s", url)
        for tmpl in get_template_list(repo_group):
            log.info("\t\t %s", tmpl)
        log.info('')


def get_purely_local_templates(storage_pool, vm_type, remote_repo):
    remote_templates = get_template_list(remote_repo)
    local_templates = get_local_templates(vm_type, storage_pool)
    return list(set(local_templates) - set(remote_templates))


def get_template_info(template_name, vm_type, storage_pool=None):
    config = get_config()
    if not storage_pool:
        storage_pool = config.getstring('general', 'default-storage-pool')
    ovf_file = OvfFile(os.path.join(storage.get_pool_path(storage_pool),
                                    vm_type, "unpacked",
                                    template_name + ".ovf"))
    vm = vm_ops.get_module(vm_type)
    template_settings = vm.get_ovf_template_settings(ovf_file)
    # XXX handle modification to system params
    #errors = vm.adjust_setting_to_systems_resources(template_settings)
    return template_settings


def get_templates_sync_list(sync_tasks_fnm=None):
    """Return current template synchronisation list"""
    if not sync_tasks_fnm:
        sync_tasks_fnm = get_config().getstring('general', 'sync_task_list')
    with open(sync_tasks_fnm, 'r') as tf:
        return pickle.load(tf)


def set_templates_sync_list(tasks, sync_tasks_fnm=None):
    """Set new template synchronisation list. Function should be handled with care,
    as some retrieval might be in progress"""
    if not sync_tasks_fnm:
        sync_tasks_fnm = get_config().getstring('general', 'sync_task_list')
    with open(sync_tasks_fnm, 'w') as tf:
        pickle.dump(tasks, tf)


def sync_templates_list(sync_tasks_fnm=None):
    """Sync a list of templates defined in a file. After synchronizing a template,
    removes it from the list. NB: multiple copies of this function should be run
    against the same task list file!"""
    if not sync_tasks_fnm:
        sync_tasks_fnm = get_config().getstring('general', 'sync_task_list')
    if os.path.exists(sync_tasks_fnm):
        tasks = get_templates_sync_list(sync_tasks_fnm)
        while tasks:
            # this doesn't make sense the first time, but for resilience we reread a list
            # each time a template was downloaded
            tasks = get_templates_sync_list(sync_tasks_fnm)
            template, storage_pool, remote_repo = tasks[0]
            # XXX a separate download hook for dumping progress to a file?
            sync_template(remote_repo, template, storage_pool)
            del tasks[0]
            set_templates_sync_list(tasks, sync_tasks_fnm)
        os.unlink(sync_tasks_fnm)


def is_syncing():
    """Return true if syncing in progress"""
    return int(execute("screen -ls 2>/dev/null | grep OPENNODE-SYNC| wc -l")) == 1


def _url_exists(url):
    """Check if remote url exists (is not 404)"""
    parsed_url = urlparse.urlparse(url)
    conn = httplib.HTTPConnection(parsed_url.netloc)
    conn.request('HEAD', parsed_url.path)
    response = conn.getresponse()
    conn.close()
    return response.status != 404
