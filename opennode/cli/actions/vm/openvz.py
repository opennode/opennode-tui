import os
import operator
import datetime
import tarfile
from os import path
from hashlib import sha1
import errno
from contextlib import closing

import libvirt
from ovf.OvfFile import OvfFile
from ovf.OvfReferencedFile import OvfReferencedFile

from opennode.cli import config
from opennode.cli.actions import sysresources as sysres
from opennode.cli.actions.vm import ovfutil
from opennode.cli.actions.utils import SimpleConfigParser, execute, get_file_size_bytes, \
                        calculate_hash
from opennode.cli.actions.vm.config_template import openvz_template


def get_ovf_template_settings(ovf_file):
    """ Parses ovf file and creates a dictionary of settings """
    settings = read_default_ovf_settings()
    ovf_settings = read_ovf_settings(ovf_file)
    settings.update(ovf_settings)
    settings["vm_id"] = _get_available_ct_id()
    return settings

def get_active_template_settings(vm_name, storage_pool):
    """ Reads ovf settings of the specified VM """
    ovf_fnm = path.join(config.c("general", "storage-endpoint"), storage_pool, 
                       "openvz", "unpacked", get_template_name(vm_name) + ".ovf")
    if path.exists(ovf_fnm):
        ovf_file = OvfFile(ovf_fnm)
        return get_ovf_template_settings(ovf_file)
    else:
        return read_default_ovf_settings()
    
def read_default_ovf_settings():
    """ Reads default ovf configuration from file, returns a dictionary of settings."""
    return dict(config.clist('ovf-defaults', 'openvz'))

def read_ovf_settings(ovf_file):
    """ Reads given ovf template configuration file, returns a dictionary of settings."""
    settings = {}
    
    settings["template_name"] = os.path.split(ovf_file.path)[1][:-4]  
    
    vm_type = ovfutil.get_vm_type(ovf_file)
    if vm_type != "openvz":
        raise Exception, "Given template is not compatible with OpenVZ on OpenNode server"
    settings["vm_type"] = vm_type
    
    memory_settings = [
        ("memory_min", ovfutil.get_ovf_min_memory_gb(ovf_file)),
        ("memory_normal", ovfutil.get_ovf_normal_memory_gb(ovf_file)),
        ("memory_max", ovfutil.get_ovf_max_memory_gb(ovf_file))]
    # set only those settings that are explicitly specified in the ovf file (non-null)
    settings.update(dict(filter(operator.itemgetter(1), memory_settings)))
    
    vcpu_settings = [
        ("vcpu_min", ovfutil.get_ovf_min_vcpu(ovf_file)),
        ("vcpu_normal", ovfutil.get_ovf_normal_vcpu(ovf_file)),
        ("vcpu_max", ovfutil.get_ovf_max_vcpu(ovf_file))]
    # set only those settings that are explicitly specified in the ovf file (non-null)
    settings.update(dict(filter(operator.itemgetter(1), vcpu_settings)))
    
    # TODO: apparently need to check disks also?
    return settings

def adjust_setting_to_systems_resources(ovf_template_settings):
    """ 
    Adjusts maximum required resources to match available system resources. 
    NB! Minimum bound is not adjusted.
    """
    st = ovf_template_settings
    st["memory_max"] = str(min(sysres.get_ram_size_gb(), float(st.get("memory_max", 10**30))))
    st["memory"] = str(min(float(st["memory"]), float(st["memory_max"])))
    
    st["swap_max"] = str(min(sysres.get_swap_size_gb(), float(st.get("swap_max", 10**30))))
    st["swap"] = str(min(float(st["swap"]), float(st["swap_max"])))
    
    st["vcpu_max"] = str(min(sysres.get_cpu_count(), int(st.get("vcpu_max", 10**10))))
    st["vcpu"] = str(min(int(st["vcpu"]), int(st["vcpu_max"])))
    
    st["vcpulimit_max"] = str(min(sysres.get_cpu_usage_limit(), int(st.get("vcpulimit_max", 100))))
    st["vcpulimit"] = str(min(int(st["vcpulimit"]), int(st["vcpulimit_max"])))
    
    st["disk_max"] = str(min(sysres.get_disc_space_gb(), float(st.get("disk_max", 10**30))))
    st["disk"] = str(min(float(st["disk"]), float(st["disk_max"])))
    
    # Checks if minimum required resources exceed maximum available resources.
    errors = []
    if float(st["memory_min"]) > float(st["memory_max"]):
        errors.append("Minimum required memory %sGB exceeds total available memory %sGB" %
                      (st["memory_min"], st["memory_max"]))
    if int(st["vcpu_min"]) > int(st["vcpu_max"]):
        errors.append("Minimum required number of vcpus %s exceeds available number %s." %
                      (st["vcpu_min"], st["vcpu_max"]))
    if int(st["vcpulimit_min"]) > int(st["vcpulimit_max"]):
        errors.append("Minimum required vcpu usage limit %s%% exceeds available %s%%." %
                      (st["vcpulimit_min"], st["vcpulimit_max"]))
    if float(st["disk_min"]) > float(st["disk_max"]):
        errors.append("Minimum required disk space %sGB exceeds available %sGB." %
                      (st["disk_min"], st["disk_max"]))
    return errors

def _get_available_ct_id():
    """
    Get next available IF for new OpenVZ CT
    
    @return: Next available ID for new OpenVZ CT
    @rtype: Integer
    """
    return max (100, max([0] + _get_openvz_ct_id_list())) + 1

def _get_openvz_ct_id_list():
    """
    Return a list of current OpenVZ CTs (both running and stopped)

    @return: List of OpenVZ containers on current machine
    @rtype: List
    """
    conn = libvirt.open("openvz:///system")
    return map(int, conn.listDefinedDomains() + conn.listDomainsID())

def _compute_diskspace_hard_limit(soft_limit):
    return soft_limit * 1.1 if soft_limit <= 10 else soft_limit + 1

def generate_ubc_config(settings):
    """ Generates UBC part of  configuration file for VZ container """
    st = settings
    ubc_params = {
        "physpages_barrier": st["memory"],
        "physpages_limit": st["memory"],
        
        "swappages_barrier": st["swap"],
        "swappages_limit": st["swap"],
        
        "diskspace_soft": st["disk"],
        "diskspace_hard": _compute_diskspace_hard_limit(float(st["disk"])),
        
        "diskinodes_soft": float(st["disk"]) *
                           int(config.c("ubc-defaults", "DEFAULT_INODES", "openvz")),
        "diskinodes_hard": round(_compute_diskspace_hard_limit(float(st["disk"])) *
                           int(config.c("ubc-defaults", "DEFAULT_INODES", "openvz"))),
                           
        "quotatime": config.c("ubc-defaults", "DEFAULT_QUOTATIME", "openvz"),
        
        "cpus": st["vcpu"],
        "cpulimit": int(st["vcpulimit"]) * int(st["vcpu"]),
        'cpuunits': config.c("ubc-defaults", "DEFAULT_CPUUNITS", "openvz"),
    }
    # Get rid of zeros where necessary (eg 5.0 - > 5 )
    ubc_params = dict([(key, int(float(val)) if float(val).is_integer() else val) 
                       for key, val in ubc_params.items()])
    ubc_params['time'] = datetime.datetime.today().ctime() 
    return  openvz_template % ubc_params

def generate_nonubc_config(conf_filename, settings):
    """ Generates Non-UBC part of  configuration file for VZ container """
    parser = SimpleConfigParser()
    parser.read(conf_filename)
    config_dict = parser.items()
    # Parameters to read. Others will be generated using ovf settings.
    include_params = ["VE_ROOT", "VE_PRIVATE", "OSTEMPLATE","ORIGIN_SAMPLE"]
    config_dict = dict((k, v) for k, v in config_dict.iteritems() if k in include_params)
    config_str = "\n".join("%s=%s" % (k, v) for k, v in config_dict.iteritems()) 
    
    # set UUID if provided
    if settings.get('uuid') is not None:
        config_str += "\n\n#UUID: %s" % settings.get('uuid')
    return config_str

def create_container(ovf_settings):
    """ Creates OpenVZ container """
    execute("vzctl create %s --ostemplate %s --config %s" % (ovf_settings["vm_id"], 
                                                           ovf_settings["template_name"],
                                                           ovf_settings["vm_id"]))
    execute("chmod 755 /vz/private/%s" % ovf_settings["vm_id"])
    # unlink base config
    base_config = os.path.join('/etc/vz/conf/', "ve-%s.conf-sample" % ovf_settings["vm_id"]) 
    os.unlink(base_config)

def generate_config(ovf_settings):
    """ Generates  ubc and non-ubc configuration """
    base_conf = os.path.join('/etc/vz/conf', "ve-vswap-256m.conf-sample")
    ubc_conf_str = generate_ubc_config(ovf_settings)
    non_ubc_conf_str = generate_nonubc_config(base_conf, ovf_settings) 
    openvz_ct_conf = "%s\n%s\n" % (ubc_conf_str, non_ubc_conf_str) # final configuration is ubc + non-ubc
    
    # overwrite configuration
    target_conf_fnm = os.path.join('/etc/vz/conf/', "ve-%s.conf-sample" % ovf_settings["vm_id"]) 
    with open(target_conf_fnm, 'w') as conf_file:
        conf_file.write(openvz_ct_conf)
    execute("chmod 644 %s" % target_conf_fnm)

def deploy(ovf_settings, storage_pool):
    """ Deploys OpenVZ container """
    # make sure we have required template present and symlinked        
    link_template(storage_pool, ovf_settings["template_name"])
    
    print "Generating configuration..."
    generate_config(ovf_settings)
    
    print "Creating OpenVZ container..."
    create_container(ovf_settings)
    
    print "Deploying..."

    nameservers = ovf_settings.get("nameservers", None)
    if not nameservers:
        nameservers = [ovf_settings["nameserver"]]

    execute("vzctl set %s %s --save" % (ovf_settings["vm_id"], ' '.join('--nameserver %s' % i for i in nameservers)))
    execute("vzctl set %s --ipadd %s --save" % (ovf_settings["vm_id"], ovf_settings["ip_address"]))
    execute("vzctl set %s --hostname %s --save" % (ovf_settings["vm_id"], ovf_settings["hostname"]))
    execute("vzctl set %s --userpasswd root:%s --save" % (ovf_settings["vm_id"], ovf_settings["passwd"]))
    execute("vzctl start %s" % (ovf_settings["vm_id"]))
    print "Template %s deployed successfully!" % ovf_settings["vm_id"]
    
def get_available_instances():
    """Return deployed and stopped OpenVZ instances"""
    vzcontainers = execute("vzlist -H -S -o ctid,hostname").split('\n')
    candidates = {}
    for cont in vzcontainers:
        if len(cont.strip()) == 0: break
        cid, hn = cont.strip().split(' ')
        candidates[int(cid)] = "%s (%s)" %(hn, cid)
    return candidates

def get_template_name(ctid):
    """Return a name of the template used for creating specific container"""
    try:
        int(ctid)
    except ValueError:
        raise RuntimeError, "Incorrect format for a container id."
    return execute("vzlist %s -H -o ostemplate" % ctid)

def get_hostname(ctid):
    """Return a hostname of the container"""
    try:
        int(ctid)
    except ValueError:
        raise RuntimeError, "Incorrect format for a container id."
    return execute("vzlist %s -H -o hostname" % ctid)

def link_template(storage_pool, tmpl_name, overwrite = True):
    """Setup symlinks from the OpenVZ template to the location expected by vzctl"""
    # added resilience. Openvz templates are distributed as tarballs, so sometimes 
    # name and name.tar.gz are used in a mixed way
    if not tmpl_name.endswith('.tar.gz'):
        tmpl_name = tmpl_name + '.tar.gz'
    source_file = os.path.join(config.c('general', 'storage-endpoint'), 
                                                  storage_pool, 'openvz', 
                                                  'unpacked', tmpl_name)
    dest_file = os.path.join(config.c('general', 'openvz-templates'), 
                             tmpl_name)
    if overwrite:
        try:
            os.unlink(dest_file)
        except OSError as exc: 
            if exc.errno != errno.ENOENT:
                raise
    if not os.path.exists(dest_file):
        os.symlink(source_file, dest_file)

def save_as_ovf(vm_settings, storage_pool):
    """
    Creates ovf template archive for the specified container. 
    Steps:
        - archive container directory
        - generate ovf configuration file
        - pack ovf and container archive into tar.gz file  
    """

    dest_dir = path.join(config.c('general', 'storage-endpoint'), storage_pool, "openvz")
    unpacked_dir = path.join(dest_dir, "unpacked")
    ct_archive_fnm = path.join(unpacked_dir, "%s.tar.gz" % vm_settings["template_name"])
    ct_source_dir = path.join("/vz/private", vm_settings["vm_name"])

    # Pack vm container catalog
    print "Archiving VM container catalog %s. This may take a while..." % ct_source_dir
    with closing(tarfile.open(ct_archive_fnm, "w:gz")) as tar:
        for file in os.listdir(ct_source_dir):
            tar.add(path.join(ct_source_dir, file), arcname=file)

    # generate and save ovf configuration file
    print "Generating ovf file..."
    ovf = _generate_ovf_file(vm_settings, ct_archive_fnm)
    ovf_fnm = path.join(unpacked_dir, "%s.ovf" % vm_settings["template_name"])
    with open(ovf_fnm, 'w') as f:
        ovf.writeFile(f, pretty=True, encoding='UTF-8')

    # pack container archive and ovf file
    print "Archiving..."
    ovf_archive_fnm = path.join(dest_dir, "%s.tar" % vm_settings["template_name"])
    with closing(tarfile.open(ovf_archive_fnm, "w")) as tar:
        tar.add(ct_archive_fnm, arcname=path.basename(ct_archive_fnm))
        tar.add(ovf_fnm, arcname=path.basename(ovf_fnm))
    
    calculate_hash(ovf_archive_fnm)
    print "Done! Saved template at %s" % ovf_archive_fnm

def _generate_ovf_file(vm_settings, ct_archive_fnm):
    ovf = OvfFile()
    ovf.createEnvelope()
    instanceId = 0
    virtualSystem = ovf.createVirtualSystem(ident=vm_settings["template_name"], 
                                            info="OpenVZ OpenNode template")
    hardwareSection = ovf.createVirtualHardwareSection(node=virtualSystem, 
                                ident="virtual_hadrware", 
                                info="Virtual hardware requirements for a virtual machine")
    ovf.createSystem(hardwareSection, "Virtual Hardware Family", str(instanceId), 
                     {"VirtualSystemType": "openvz"})
    instanceId += 1

    # add cpu section
    for bound, cpu in zip(["normal", "min", "max"],
                          [vm_settings.get("vcpu%s" % pfx) for pfx in ["", "_min", "_max"]]):
        if cpu:
            ovf.addResourceItem(hardwareSection, {
                "Caption": "%s virtual CPU" % cpu,
                "Description": "Number of virtual CPUs",
                "ElementName": "%s virtual CPU" % cpu,
                "InstanceID": str(instanceId),
                "ResourceType": "3",
                "VirtualQuantity": cpu
                }, bound=bound)
            instanceId += 1

    # add memory section
    for bound, memory in zip(["normal", "min", "max"],
                             [vm_settings.get("memory%s" % pfx) for pfx in ["", "_min", "_max"]]):
        if memory:
            ovf.addResourceItem(hardwareSection, {
                "AllocationUnits": "GigaBytes",
                "Caption": "%s GB of memory" % memory,
                "Description": "Memory Size",
                "ElementName": "%s GB of memory" % memory,
                "InstanceID": str(instanceId),
                "ResourceType": "4",
                "VirtualQuantity": memory
                }, bound=bound)
            instanceId += 1
    
    def get_checksum(fnm):
        # calculate checksum for the file 
        chunk_size = 1024 ** 2 # 1Mb 
        sha = sha1()
        with open(fnm) as chkfile:
            while 1:
                data = chkfile.read(chunk_size)
                if not data:
                    break
                sha.update(data)
        return sha.hexdigest()
    
    # add reference a file (see http://gitorious.org/open-ovf/mainline/blobs/master/py/ovf/OvfReferencedFile.py)
    ref_file = OvfReferencedFile(path.dirname(ct_archive_fnm), 
                                 path.basename("%s.tar.gz" % vm_settings["template_name"]), 
                                 file_id="diskfile1",
                                 size=str(get_file_size_bytes(ct_archive_fnm)),
                                 compression="gz",
                                 checksum=get_checksum(ct_archive_fnm))
    ovf.addReferencedFile(ref_file)
    ovf.createReferences()
    
    def get_ct_disk_usage_bytes(ctid):
        return str(int(execute("du -s /vz/private/%s/" % ctid).split()[0]) * 1024)
    
    # add disk section
    ovf.createDiskSection([{
        "diskId": "vmdisk1", 
        "capacity": str(round(float(vm_settings["disk"]) * 1024 ** 3)), # in bytes
        "capacityAllocUnits": None, # bytes default
        "populatedSize": get_ct_disk_usage_bytes(vm_settings["vm_name"]),
        "fileRef": "diskfile1",
        "parentRef": None,
        "format": "tar.gz"}],
        "OpenVZ CT template disks")
    return ovf

def get_memory(ctid):
    """Max memory in MB"""
    res = int(execute("vzlist %s -H -o privvmpages.l" % ctid)) * 4 / 1024
    if res >= 2**31:
        res = int(execute("vzlist %s -H -o physpages.l" % ctid)) * 4 / 1024
    return res

def get_diskspace(ctid):
    """Max disk space in MB"""
    return float(execute("vzlist %s -H -o diskspace.h" % ctid))  / 1024

def get_uptime(ctid):
    """Get uptime in seconds"""
    return float(execute("vzctl exec %s \"awk '{print \$1}' /proc/uptime\"" % ctid))
