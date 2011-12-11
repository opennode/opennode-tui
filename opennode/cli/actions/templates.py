import urllib
import urllib2
import tarfile
import os
import shutil
import re

from ovf.OvfFile import OvfFile

from opennode.cli.config import c
from opennode.cli.utils import delete, calculate_hash
from opennode.cli.actions import storage, vm as vm_ops
from opennode.cli import config 


__all__ = ['get_template_repos', 'get_template_list', 'sync_storage_pool',
           'sync_template', 'delete_template', 'unpack_template',
           'get_local_templates', 'sync_oms_template', 'is_fresh',
           'prepare_storage_pool']


def _simple_download_hook(count, blockSize, totalSize):
    """Simple download counter"""
    print "% 3.1f%% of %d bytes\r" % (min(100, float(blockSize * count) / totalSize * 100), totalSize),

def get_template_repos():
    """Return a formatted list of strings describing configured repositories"""
    repo_groups = c('general', 'repo-groups').split(',')
    result = []
    for r in repo_groups:
        group = "%s-repo" % r.strip()
        name = c(group, 'name')
        vm_type = c(group, 'type')
        result.append(("%s (%s)" %(name, vm_type), group))
    return result

def get_template_list(remote_repo):
    """Retrieves a tmpl_list of templates from the specified repository"""
    url = c(remote_repo, 'url')
    tmpl_list = urllib2.urlopen("%s/templatelist.txt" % url)
    templates = [template.strip() for template in tmpl_list]
    tmpl_list.close()
    return templates

def sync_storage_pool(storage_pool, remote_repo, templates, download_monitor = None):
    """Synchronize selected storage pool with the remote repo. Only selected templates 
    will be persisted, all of the other templates shall be purged"""
    vm_type = c(remote_repo, 'type')
    existing_templates = get_local_templates(vm_type, storage_pool)
    # synchronize selected templates
    if templates is None: templates = []
    purely_local_tmpl = get_purely_local_templates(storage_pool, vm_type, remote_repo)
    for tmpl in templates:
        if tmpl in purely_local_tmpl: 
            continue
        sync_template(remote_repo, tmpl, storage_pool, download_monitor)
        if tmpl in existing_templates:
            existing_templates.remove(tmpl)
    # delete existing, but not selected templates
    for tmpl in existing_templates:
        delete_template(storage_pool, vm_type, tmpl)


def sync_template(remote_repo, template, storage_pool, download_monitor = None):
    """Synchronizes local template (cache) with the remote one (master)"""
    url = c(remote_repo, 'url')
    vm_type = c(remote_repo, 'type')
    storage_endpoint = c('general', 'storage-endpoint')
    localfile = os.path.join(storage_endpoint, storage_pool, vm_type, template)
    remotefile = os.path.join(url, template)
    # only download if we don't already have a fresh copy
    if not is_fresh(localfile, remotefile):
        # for resilience
        storage.prepare_storage_pool(storage_pool)
        if download_monitor is None:
            download_hook = _simple_download_hook
        else:
            download_monitor.update_url(template)
            download_hook = download_monitor.download_hook
        urllib.urlretrieve("%s.tar" % remotefile, "%s.tar" % localfile, download_hook)
        urllib.urlretrieve("%s.tar.pfff" % remotefile, "%s.tar.pfff" % localfile,
                           download_hook)
        unpack_template(storage_pool, vm_type, localfile)

def import_template(template, vm_type, storage_pool = c('general', 'default-storage-pool')):
    """Import external template into ON storage pool"""
    if not os.path.exists(template):
        raise RuntimeError("Template not found: " % template)
    if not template.endswith('tar'):
        raise RuntimeError("Expecting a file ending with .tar for a template")
    storage_endpoint = c('general', 'storage-endpoint')
    target_file = os.path.join(storage_endpoint, storage_pool, vm_type, template)
    print "Copying template to the storage pool..."
    print template, target_file
    shutil.copyfile(template, target_file)
    calculate_hash(target_file)
    print "Unpacking..."
    unpack_template(storage_pool, vm_type, template)

def delete_template(storage_pool, vm_type, template):
    """Deletes template, unpacked folder and a hash"""
    # get a list of files in the template
    storage_endpoint = c('general', 'storage-endpoint')
    templatefile = "%s/%s/%s/%s.tar" % (storage_endpoint, storage_pool, vm_type, 
                                        template)
    tmpl = tarfile.open(templatefile)
    for packed_file in tmpl.getnames():
        fnm = "%s/%s/%s/unpacked/%s" % (storage_endpoint, storage_pool, vm_type, 
                                        packed_file)
        if not os.path.isdir(fnm):
            delete(fnm)
        else:
            shutil.rmtree(fnm)
    # remove master copy
    delete(templatefile)
    delete("%s.pfff" % templatefile)
    # also remove symlink for openvz vm_type
    if vm_type == 'openvz':
        delete("%s/%s" % (c('general', 'openvz-templates'), "%s.tar.gz" % template))

def unpack_template(storage_pool, vm_type, tmpl_name):
    """Unpacks template into the 'unpacked' folder of the storage pool. 
       Adds symlinks as needed by the VM template vm_type."""
    # we assume location of the 'unpacked' to be the same as the location of the file
    basedir = os.path.join(c('general', 'storage-endpoint'), storage_pool, vm_type)
    tmpl = tarfile.open(os.path.join(basedir, tmpl_name))
    unpacked_dir = os.path.join(basedir, 'unpacked')
    tmpl.extractall(unpacked_dir)
    # special case for openvz vm_type
    if vm_type == 'openvz':
        from opennode.cli.actions import vm
        tmpl_name = [fnm for fnm in tmpl.getnames() if fnm.endswith('tar.gz')]
        # make sure we have only a single tarball with the image
        assert len(tmpl_name) == 1
        vm.openvz.link_template(storage_pool, tmpl_name[0])

def get_local_templates(vm_type, storage_pool = c('general', 'default-storage-pool')):
    """Returns a list of templates of a certain vm_type from the storage pool"""
    storage_endpoint = c('general', 'storage-endpoint')
    return [tmpl[:-4] for tmpl in os.listdir("%s/%s/%s" % (storage_endpoint,
                                storage_pool, vm_type)) if tmpl.endswith('tar')]

def sync_oms_template(storage_pool = c('general', 'default-storage-pool')):
    """Synchronize OMS template"""
    repo = c('opennode-oms-template', 'repo')
    tmpl = c('opennode-oms-template', 'template_name')
    sync_template(repo, tmpl, storage_pool)

def is_fresh(localfile, remotefile):
    """Checks whether local copy matches remote file"""
    # get remote hash
    remote_hashfile = urllib2.urlopen("%s.tar.pfff" % remotefile)
    remote_hash = remote_hashfile.read()
    remote_hashfile.close()
    # get a local one
    try:
        with open("%s.tar.pfff" % localfile, 'r') as f:
            local_hash = f.read()
    except IOError:
        # no local hash found
        return False 
    return remote_hash == local_hash

def list_templates():
    """ Prints all local and remote templates """
    # local templates
    for vm_type in ["openvz", "kvm"]:
        print "%s local templates:" % vm_type.upper()
        for storage_pool in storage.list_pools():
            print "\t", "Storage:", os.path.join(config.c("general", "storage-endpoint"), 
                                                 storage_pool, vm_type)  
            for tmpl in get_local_templates(storage_pool, vm_type):
                print "\t\t", tmpl
            print
    # remote templates
    repo_groups = re.split(",\s*", config.c("general", "repo-groups"))
    repo_groups = [repo_group + "-repo" for repo_group in repo_groups]
    for repo_group in repo_groups:
        url, vm_type = config.c(repo_group, "url"), config.c(repo_group, "type")
        print "%s remote templates:" % vm_type.upper()
        print "\t", "Repository:", url
        for tmpl in get_template_list(repo_group):
            print "\t\t",  tmpl
        print

def get_purely_local_templates(storage_pool, vm_type, remote_repo):
    remote_templates = get_template_list(remote_repo)
    local_templates = get_local_templates(vm_type, storage_pool)
    return list(set(local_templates) - set(remote_templates))
    
def get_template_info(template_name, vm_type, storage_pool = c('general', 'default-storage-pool')):
    ovf_file = OvfFile(os.path.join(c("general", "storage-endpoint"),
                                        storage_pool, vm_type, "unpacked", 
                                        template_name + ".ovf"))
    vm = vm_ops.get_module(vm_type)
    template_settings = vm.get_ovf_template_settings(ovf_file)
    # XXX handle modification to system params
    #errors = vm.adjust_setting_to_systems_resources(template_settings)
    return template_settings
        