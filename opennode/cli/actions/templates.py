import urllib
import urllib2
import tarfile
import os
import shutil

from opennode.cli.config import c
from opennode.cli.utils import mkdir_p

def get_template_repos():
    """Return a formatted list of strings describing configured repositories"""
    repo_groups = c('general', 'repo-groups').split(',')
    result = []
    for r in repo_groups:
        group = "%s-repo" % r.strip()
        name = c(group, 'name')
        type = c(group, 'type')
        result.append(("%s (%s)" %(name, type), group))
    return result

def get_template_list(remote_repo):
    """Retrieves a list of templates from the specified repository"""
    url = c(remote_repo, 'url')
    list = urllib2.urlopen("%s/templatelist.txt" % url)
    templates = [template.strip() for template in list]
    list.close()
    return templates

def sync_template(remote_repo, template, storage_pool):
    """Synchronizes local template (cache) with the remote one (master)"""
    url = c(remote_repo, 'url')
    type = c(remote_repo, 'type')
    localfile = "/".join([storage_pool, type, template])
    remotefile =  "/".join([url, template])
    # only download if we don't already have a fresh copy
    if not is_fresh(localfile, remotefile):        
       prepare_storage_pool(storage_pool)
       urllib.urlretrieve("%s.tar" % remotefile, "%s.tar" % localfile, _download_hook)
       urllib.urlretrieve("%s.tar.pfff" % remotefile, "%s.tar.pfff" % localfile, _download_hook)
       unpack_template("%s.tar" % localfile, type)

def delete_template(storage_pool, type, template):
    """Deletes template, unpacked folder and a hash"""
    # get a list of files in the template
    templatefile = "%s/%s/%s.tar" % (storage_pool, type, template)
    tmpl = tarfile.open(templatefile)
    for packed_file in tmpl.getnames():
        fnm = "%s/%s/unpacked/%s" % (storage_pool, type, packed_file)
        if not os.path.isdir(fnm): 
            os.unlink(fnm)
        else:
            shutil.rmtree(fnm)
    # remove master copy
    os.unlink(templatefile)
    os.unlink("%s.pfff" % templatefile)
    # also remove symlink for openvz type
    if type == 'openvz':
        os.unlink("%s/%s" % (c('general', 'openvz-templates'), "%s.tar.gz" % template))

def unpack_template(templatefile, type):
    """Unpacks template into the 'unpacked' folder of the storage pool. 
       Adds symlinks as needed by the VM template type."""
    # we assume location of the 'unpacked' to be the same as the location of the file
    tmpl = tarfile.open(templatefile)
    unpacked_dir = os.path.dirname(templatefile)
    tmpl.extractall("%s/unpacked" % unpacked_dir)
    # special case for openvz type
    if type == 'openvz':
        tmpl_file = [fnm for fnm in tmpl.getnames() if fnm.endswith('tar.gz')]
        assert len(tmpl_file) == 1
        os.symlink("%s/unpacked/%s" % (unpacked_dir, tmpl_file[0]), "%s/%s" % (c('general', 'openvz-templates'), tmpl_file[0]))

def get_local_templates(storage_pool, type):
    """Returns a list of templates of a certain type from the storage pool"""
    return [tmpl[:-4] for tmpl in os.listdir("%s/%s" % (storage_pool, type)) if tmpl.endswith('tar')]

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

def prepare_storage_pool(storage_pool):
    """Assures that storage pool has the correct folder structure"""
    # create structure
    mkdir_p("%s/iso/" % storage_pool)
    mkdir_p("%s/images/" % storage_pool)
    mkdir_p("%s/openvz/unpacked" % storage_pool)
    mkdir_p("%s/kvm/unpacked" % storage_pool)

def _download_hook(count, blockSize, totalSize):
    """Simple download counter"""
    print "% 3.1f%% of %d bytes\r" % (min(100, float(blockSize * count) / totalSize * 100), totalSize),
    
