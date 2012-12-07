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

from opennode.cli.config import get_config
from opennode.cli.actions import sysresources as sysres
from opennode.cli.actions.vm import ovfutil
from opennode.cli.actions import oms
from opennode.cli.actions.utils import SimpleConfigParser, execute, get_file_size_bytes, \
                        calculate_hash, CommandException, TemplateException, test_passwordless_ssh, execute2
from opennode.cli.actions.vm.config_template import openvz_template
from opennode.cli.actions.network import list_nameservers
import shutil


def get_ovf_template_settings(ovf_file):
    """ Parses ovf file and creates a dictionary of settings """
    settings = read_default_ovf_settings()
    ovf_settings = read_ovf_settings(ovf_file)
    settings.update(ovf_settings)
    settings["vm_id"] = _get_available_ct_id()
    # In case of template, both next items should be at default values
    settings["bind_mounts"] = get_bmounts(settings["vm_id"])
    settings["ioprio"] = 4
    return settings


def get_active_template_settings(vm_name, storage_pool):
    """ Reads ovf settings of the specified VM """
    ovf_fnm = path.join(get_config().getstring("general", "storage-endpoint"), storage_pool,
                       "openvz", "unpacked",
                       get_template_name(vm_name) + ".ovf")
    if path.exists(ovf_fnm):
        ovf_file = OvfFile(ovf_fnm)
        return get_ovf_template_settings(ovf_file)
    else:
        return read_default_ovf_settings()


def read_default_ovf_settings():
    """
    Reads default ovf configuration from file, returns a dictionary of
    settings.
    """
    return dict(get_config().getlist('ovf-defaults', 'openvz'))


def read_ovf_settings(ovf_file):
    """
    Reads given ovf template configuration file, returns a dictionary
    of settings.
    """
    settings = {}

    settings["template_name"] = os.path.split(ovf_file.path)[1][:-4]

    vm_type = ovfutil.get_vm_type(ovf_file)
    if vm_type != "openvz":
        raise RuntimeError("Given template is not compatible with OpenVZ on OpenNode server")
    settings["vm_type"] = vm_type

    memory_settings = [
        ("memory_min", ovfutil.get_ovf_min_memory_gb(ovf_file)),
        ("memory", ovfutil.get_ovf_normal_memory_gb(ovf_file)),
        ("memory_max", ovfutil.get_ovf_max_memory_gb(ovf_file))]

    # set only those settings that are explicitly specified in the ovf file (non-null)
    settings.update(dict(filter(operator.itemgetter(1), memory_settings)))

    vcpu_settings = [
        ("vcpu_min", ovfutil.get_ovf_min_vcpu(ovf_file)),
        ("vcpu", ovfutil.get_ovf_normal_vcpu(ovf_file)),
        ("vcpu_max", ovfutil.get_ovf_max_vcpu(ovf_file))]
    # set only those settings that are explicitly specified in the ovf file (non-null)
    settings.update(dict(filter(operator.itemgetter(1), vcpu_settings)))

    settings["ostemplate"] = ovfutil.get_ovf_os_type(ovf_file)

    # TODO: apparently need to check disks also?
    return settings


def adjust_setting_to_systems_resources(ovf_template_settings):
    """
    Adjusts maximum required resources to match available system resources.
    NB! Minimum bound is not adjusted.
    """

    def adjusted(norm, minvalue, maxvalue, valtype):
        if minvalue is None:
            minvalue = 0
        if maxvalue is None:
            maxvalue = 10 * 30
        return min(max(valtype(norm), valtype(minvalue)), valtype(maxvalue))

    st = ovf_template_settings
    st["memory_max"] = min(sysres.get_ram_size_gb(), float(st.get("memory_max", 10 ** 30)))
    st["memory"] = adjusted(st.get("memory"), st.get("memory_min"), st.get("memory_max"), float)

    st["swap_max"] = str(min(sysres.get_swap_size_gb(), float(st.get("swap_max", 10 ** 30))))
    st["swap"] = adjusted(st.get("swap"), st.get("swap_min"), st.get("swap_max"), float)

    st["vcpu_max"] = str(min(sysres.get_cpu_count(), int(st.get("vcpu_max", 10 ** 10))))
    st["vcpu"] = adjusted(st.get("vcpu"), st.get("vcpu_min"), st.get("vcpu_max"), int)

    st["vcpulimit_max"] = min(sysres.get_cpu_usage_limit(), int(st.get("vcpulimit_max", 100)))
    st["vcpulimit"] = adjusted(st.get("vcpulimit"), st.get("vcpulimit_min"), st.get("vcputlimit_max"), int)

    st["disk_max"] = min(sysres.get_disc_space_gb(), float(st.get("disk_max", 10 ** 30)))
    st["disk"] = adjusted(st.get("disk"), st.get("disk_min"), st.get("disk_max"), float)

    dns = list_nameservers()
    if len(dns) > 0:
        st["nameserver"] = dns[0]
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
    return max(100, max([0] + _get_openvz_ct_id_list())) + 1


def _get_openvz_ct_id_list():
    """
    Return a list of current OpenVZ CTs (both running and stopped)

    @return: List of OpenVZ containers on current machine
    @rtype: List
    """
    existing = [ctid.strip() for ctid in execute("vzlist --all -H -o ctid").splitlines()]
    return map(int, existing)


def _compute_diskspace_hard_limit(soft_limit):
    return soft_limit * 1.1 if soft_limit <= 10 else soft_limit + 1


def generate_ubc_config(settings):
    """ Generates UBC part of configuration file for VZ container """
    config = get_config("openvz")
    st = settings
    ubc_params = {
        "physpages_limit": st["memory"],

        "swappages_limit": st["swap"],

        "diskspace_soft": st["disk"],
        "diskspace_hard": _compute_diskspace_hard_limit(float(st["disk"])),

        "diskinodes_soft": float(st["disk"]) *
                           int(config.getstring("ubc-defaults", "DEFAULT_INODES")),
        "diskinodes_hard": round(_compute_diskspace_hard_limit(float(st["disk"])) *
                           int(config.getstring("ubc-defaults", "DEFAULT_INODES"))),

        "quotatime": config.string("ubc-defaults", "DEFAULT_QUOTATIME"),

        "cpus": st["vcpu"],
        "cpulimit": int(st["vcpulimit"]) * int(st["vcpu"]),
        'cpuunits': config.getstring("ubc-defaults", "DEFAULT_CPUUNITS"),
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
    include_params = ["VE_ROOT", "VE_PRIVATE", "OSTEMPLATE", "ORIGIN_SAMPLE"]
    config_dict = dict((k, v) for k, v in config_dict.iteritems() if k in include_params)
    config_str = "\n".join("%s=%s" % (k, v) for k, v in config_dict.iteritems())

    # set UUID if provided
    if settings.get('uuid'):
        config_str += "\n\n#UUID: %s" % settings.get('uuid')

    # Add ON_BMOUNT if needed
    if settings.get('bind_mounts'):
        config_str += "\nON_BMOUNT=\"%s\"" % settings.get('bind_mounts')
    return config_str


def create_container(ovf_settings):
    """ Creates OpenVZ container """
    execute("vzctl create %s --ostemplate %s --config %s" % (ovf_settings["vm_id"],
                                                           ovf_settings["template_name"],
                                                           ovf_settings["vm_id"]))
    # replace ostemplate with a provided value, as vzctl sets the filename
    # of the packaged template, which is in general not reliable
    execute("sed -i 's/OSTEMPLATE=\"%s\"/OSTEMPLATE=\"%s\"/' %s" % (ovf_settings["template_name"],
                                                           ovf_settings["ostemplate"],
                                                           "/etc/vz/conf/%s.conf" % ovf_settings["vm_id"]
                                                           )
            )
    execute("chmod 755 /vz/private/%s" % ovf_settings["vm_id"])
    # unlink base config
    base_config = os.path.join('/etc/vz/conf/', "ve-%s.conf-sample" % ovf_settings["vm_id"])
    os.unlink(base_config)


def setup_scripts(vm_settings, storage_pool):
    """Setup action scripts for the CT"""
    dest_dir = path.join(get_config().getstring('general', 'storage-endpoint'), storage_pool, "openvz")
    unpacked_dir = path.join(dest_dir, "unpacked")
    ct_scripts_fnm = path.join(unpacked_dir, "%s.scripts.tar.gz" % vm_settings["template_name"])
    dest_folder = '/etc/vz/conf/%s' % vm_settings['vm_id']
    try:
        with closing(tarfile.open(ct_scripts_fnm, "r:gz")) as tar:
            for f in tar:
                target_script = '%s.%s' % (dest_folder, f.name)
                shutil.copyfileobj(tar.extractfile(f), open(target_script, 'w'))
                os.chmod(target_script, 0755)
    except:
        print "No action scripts in the template."
        pass


def generate_config(ovf_settings):
    """ Generates  ubc and non-ubc configuration """
    base_conf = os.path.join('/etc/vz/conf', "ve-vswap-256m.conf-sample")
    ubc_conf_str = generate_ubc_config(ovf_settings)
    non_ubc_conf_str = generate_nonubc_config(base_conf, ovf_settings)
    openvz_ct_conf = "%s\n%s\n" % (ubc_conf_str, non_ubc_conf_str)  # final configuration is ubc + non-ubc

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

    print "Setting up action scripts..."
    setup_scripts(ovf_settings, storage_pool)

    if ovf_settings.get('appliance_type') == 'oms':
        oms.configure_oms_vm(ovf_settings["vm_id"], ovf_settings["hostname"])

    if ovf_settings.get("startvm", 0) == 1:
        execute("vzctl start %s" % (ovf_settings["vm_id"]))

    if ovf_settings.get("onboot", 0) == 1:
        execute("vzctl set %s --onboot yes --save" % (ovf_settings["vm_id"]))
    else:
        execute("vzctl set %s --onboot no --save" % (ovf_settings["vm_id"]))

    if ovf_settings.get("ioprio", 4):
        execute("vzctl set %s --ioprio %d --save" % (ovf_settings["vm_id"], ovf_settings["ioprio"]))

    print "Template %s deployed successfully!" % ovf_settings["vm_id"]


def query_openvz(include_running=False, fields='ctid,hostname'):
    """Run a query against OpenVZ"""
    include_flag = '-S' if not include_running else '-a'
    vzcontainers = execute("vzlist -H %s -o %s" % (include_flag, fields)).split('\n')
    result = []
    for cont in vzcontainers:
        if len(cont.strip()) == 0:
            break
        result.append([f for f in cont.strip().split(' ') if len(f) > 0])
    return result


def get_available_instances():
    """Return deployed and stopped OpenVZ instances"""
    resources = query_openvz(False, "ctid,hostname")
    candidates = {}
    for r in resources:
        cid, hn = r
        candidates[int(cid)] = "%s (%s)" % (hn, cid)
    return candidates


def get_all_instances():
    """Return all OpenVZ instances and their parameters"""
    resources = query_openvz(False, "ctid,hostname,status")
    candidates = {}
    for r in resources:
        candidates[r[0]] = {"vm_id": r[0],
                                 "name": r[1],
                                 "status": r[2],
                                 "memory": get_memory(r[0]) / 1024,
                                 "disk": get_diskspace(r[0]) / 1024,
                                 "vcpu": get_vcpu(r[0]),
                                 "vm_type": "openvz"
                                 }
    return candidates


def get_template_name(ctid):
    """Return a name of the template used for creating specific container"""
    try:
        int(ctid)
    except ValueError:
        raise TemplateException("Incorrect format for a container id: %s" % ctid)
    return execute("vzlist %s -H -o ostemplate" % ctid)


def get_hostname(ctid):
    """Return a hostname of the container"""
    try:
        int(ctid)
    except ValueError:
        raise TemplateException("Incorrect format for a container id: %s" % ctid)
    return execute("vzlist %s -H -o hostname" % ctid)


def link_template(storage_pool, tmpl_name, overwrite=True):
    """Setup symlinks from the OpenVZ template to the location expected by vzctl"""
    # added resilience. Openvz templates are distributed as tarballs, so sometimes
    # name and name.tar.gz are used in a mixed way
    config = get_config()
    if not tmpl_name.endswith('.tar.gz'):
        tmpl_name = tmpl_name + '.tar.gz'
    source_file = os.path.join(config.getstring('general', 'storage-endpoint'),
                                                  storage_pool, 'openvz',
                                                  'unpacked', tmpl_name)
    dest_file = os.path.join(config.getstring('general', 'openvz-templates'), tmpl_name)
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
    dest_dir = path.join(get_config().getstring('general', 'storage-endpoint'), storage_pool, "openvz")
    unpacked_dir = path.join(dest_dir, "unpacked")
    ct_archive_fnm = path.join(unpacked_dir, "%s.tar.gz" % vm_settings["template_name"])
    ct_source_dir = path.join("/vz/private", vm_settings["vm_name"])

    # Pack vm container catalog
    print "Archiving VM container catalog %s. This may take a while..." % ct_source_dir
    with closing(tarfile.open(ct_archive_fnm, "w:gz")) as tar:
        for f in os.listdir(ct_source_dir):
            tar.add(path.join(ct_source_dir, f), arcname=f)

    # Archive action scripts if they are present
    print "Adding action scripts..."
    ct_scripts_fnm = path.join(unpacked_dir, "%s.scripts.tar.gz" % vm_settings["template_name"])
    with closing(tarfile.open(ct_scripts_fnm, "w:gz")) as tar:
        for script_type in ['premount', 'mount', 'start', 'stop', 'umount', 'postumount']:
            script_fnm = "/etc/vz/conf/%s.%s" % (vm_settings["vm_name"], script_type)
            if os.path.exists(script_fnm):
                tar.add(script_fnm, arcname=script_type)

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
        tar.add(ct_scripts_fnm, arcname=path.basename(ct_scripts_fnm))

    calculate_hash(ovf_archive_fnm)
    print "Done! Saved template at %s" % ovf_archive_fnm


def _generate_ovf_file(vm_settings, ct_archive_fnm):
    ovf = OvfFile()
    ovf.createEnvelope()
    instanceId = 0
    virtualSystem = ovf.createVirtualSystem(ident=vm_settings["template_name"],
                                            info="OpenVZ OpenNode template")
    # add OS section
    ovf.createOperatingSystem(node=virtualSystem,
                              ident='operating_system',
                              info='Operating system type deployed in a template',
                              description=vm_settings.get('ostemplate', 'linux'))

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
        chunk_size = 1024 ** 2  # 1Mb
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
        "capacity": str(round(float(vm_settings["disk"]) * 1024 ** 3)),  # in bytes
        "capacityAllocUnits": None,  # bytes default
        "populatedSize": get_ct_disk_usage_bytes(vm_settings["vm_name"]),
        "fileRef": "diskfile1",
        "parentRef": None,
        "format": "tar.gz"}],
        "OpenVZ CT template disks")
    return ovf


def get_swap(ctid):
    """Swap memory in MB"""
    return int(execute("vzlist %s -H -o swappages.l" % ctid)) * 4 / 1024


def get_memory(ctid):
    """Max memory in MB"""
    res = int(execute("vzlist %s -H -o privvmpages.l" % ctid)) * 4 / 1024
    if res >= 2 ** 31:
        res = int(execute("vzlist %s -H -o physpages.l" % ctid)) * 4 / 1024
    return res


def get_diskspace(ctid):
    """Max disk space in MB"""
    return float(execute("vzlist %s -H -o diskspace.h" % ctid)) / 1024


def get_onboot(ctid):
    """Return onboot parameter of a specified CT"""
    encoding = {"yes": 1,
                "no": 0}
    return encoding[execute("vzlist %s -H -o onboot" % ctid).strip()]


def get_bootorder(ctid):
    """Return the boot order of the container or None, if it's not defined"""
    order = execute("vzlist %s -H -o bootorder" % ctid).strip()
    return int(order) if order.isdigit() else ''


def get_uptime(ctid):
    """Get uptime in seconds. 0 if container is not running."""
    try:
        return float(execute("vzctl exec %s \"awk '{print \$1}' /proc/uptime\"" % ctid))
    except:
        return 0


def get_cpulimit(ctid):
    """Max CPU usage limit"""
    return int(execute("vzlist %s -H -o cpulimit" % ctid))


def detect_os(ctid):
    """Detect OS name running in a VM"""
    return execute("vzctl runscript %s `which detect-os`" % ctid)


def get_vcpu(ctid):
    """Return number of virtual CPUs as seen by the VM"""
    return int(execute("vzlist %s -H -o cpus" % ctid))


def get_ioprio(ctid):
    """ Get VM I/O priority. If priority is entered manually
    or elsewhere, return approximate value based on value table"""
    value = { '0': 0,
              '1': 0,
              '2': 0,
              '3': 0,
              '4': 4,
              '5': 7,
              '6': 7,
              '7': 7,}
    rv = execute("vzlist %s -H -o ioprio" % ctid).strip()
    if rv == '-':
        return 4
    else:
        return value[rv]


def _update_bmounts(vm_id, bind_mounts):
    conf_fnm = '/etc/vz/conf/%s.conf' % vm_id
    condition = False
    with file(conf_fnm, 'rt') as f:
        data = f.read()
    data = data.split('\n')
    for line in enumerate(data):
        if line[1].count('ON_BMOUNT') and not line[1].strip().startswith('#'):
            data[line[0]] = 'ON_BMOUNT="%s"' % bind_mounts
            condition = True
    if not condition:
        data.append('ON_BMOUNT="%s"' % bind_mounts)
    with file(''.join([conf_fnm, '.new']), 'wt') as f:
        f.write('\n'.join(data))
    os.rename(conf_fnm, ''.join([conf_fnm, '.bak']))
    os.rename(''.join([conf_fnm, '.new']), conf_fnm)


def update_vm(settings):
    """Perform modifications to the VM virtual hardware"""
    vm_id = get_ctid_by_uuid(settings["uuid"])
    if settings.get("diskspace"):
        disk = float(settings["diskspace"])
        execute("vzctl set %s --diskspace %sG --save" % (vm_id, disk))
    if settings.get("vcpu"):
        execute("vzctl set %s --cpus %s --save" % (vm_id, int(settings.get("vcpu"))))
    if settings.get("memory"):
        mem = float(settings.get("memory"))
        execute("vzctl set %s --ram %sG --save" % (vm_id, mem))
    if settings.get("swap"):
        mem = float(settings.get("swap"))
        execute("vzctl set %s --swap %sG --save" % (vm_id, mem))
    if "onboot" in settings:
        vals = {0: "no",
                1: "yes"}
        execute("vzctl set %s --onboot %s --save" % (vm_id,
                                                     vals[settings["onboot"]]))
    if settings.get("bootorder"):
        order = int(settings.get("bootorder"))
        execute("vzctl set %s --bootorder %s --save" % (vm_id, order))

    if settings.get("vcpulimit"):
        vcpulimit = int(settings.get("vcpulimit"))
        execute("vzctl set %s --cpulimit %s --save" % (vm_id, vcpulimit))

    if settings.get("bind_mounts") is not None:
        _update_bmounts(vm_id, settings["bind_mounts"])

    if settings.get("ioprio") is not None:
        ioprio = int(settings.get("ioprio"))
        if settings.get("ioprio_old") is not None:
            if ioprio != int(settings.get("ioprio_old")):
                execute("vzctl set %s --ioprio %s --save" % (vm_id, ioprio))
        else:
            execute("vzctl set %s --ioprio %s --save" % (vm_id, ioprio))


def get_uuid_by_ctid(ctid):
    """Return UUID of the VM"""
    return execute("grep \#UUID: /etc/vz/conf/%s.conf" % ctid).split(" ")[1]


def get_ctid_by_uuid(uuid, backend='openvz:///system'):
    """Return container ID with a given UUID"""
    conn = libvirt.open(backend)
    return conn.lookupByUUIDString(uuid).name()


def get_bmounts(ctid):
    """Return ON_BMOUNT for the VM with given CTID"""
    parser = SimpleConfigParser()
    try:
        parser.read('/etc/vz/conf/%s.conf' % ctid)
    except IOError:
        # File not found in case we are doing a new conf
        return ''
    conf = parser.items()
    if conf.has_key('ON_BMOUNT'):
        if conf['ON_BMOUNT'].strip().startswith('"'):
            conf['ON_BMOUNT'] = conf['ON_BMOUNT'][1:]
        if conf['ON_BMOUNT'].strip().endswith('"'):
            conf['ON_BMOUNT'] = conf['ON_BMOUNT'][:-1]
        return conf['ON_BMOUNT']
    else:
        return ''


def shutdown_vm(uuid):
    """Shutdown VM with a given UUID"""
    ctid = get_ctid_by_uuid(uuid)
    try:
        print execute("vzctl stop %s" % ctid)
    except CommandException as e:
        if e.code == 13056:  # sometimes umount fails
            for i in range(5):
                try:
                    print execute("vzctl umount %s" % ctid)
                except CommandException:
                    import time
                    time.sleep(3)


def get_vzcpucheck():
    """Return CPU utilization of the node. (used, total)"""
    return tuple([int(v.strip()) for v in execute('vzcpucheck|cut -f 2 -d ":"').split("\n")])


def migrate(uid, target_host, live=False):
    """Migrate given container to a target_host"""
    if not test_passwordless_ssh(target_host):
        raise CommandException("Public key ssh connection with the target host could not be established")
    # is ctid present on the target host?
    ctid = get_ctid_by_uuid(uid)
    try:
        execute("ssh %s vzlist %s" % (target_host, ctid))
        raise CommandException("Target host '%s' already has a defined CTID '%s'" % (target_host, ctid))
    except CommandException as ce:
        if ce.code == 256:
            pass
        else:
            raise ce
    print "Initiating migration to %s..." % target_host
    live_trigger = '--online' if live else ''
    for line in execute2("vzmigrate -v %s %s %s" % (live_trigger, target_host, ctid)):
        print line
