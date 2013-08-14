"""
@note: open-ovf api: http://gitorious.org/open-ovf/
"""

import os
from ovf import Ovf, OvfLibvirt

from opennode.cli.actions.utils import calculate_hash, save_to_tar
from opennode.cli.config import get_config


def get_vm_type(ovf_file):
    return ovf_file.document.getElementsByTagName("vssd:VirtualSystemType")[0].firstChild.nodeValue


def get_ovf_os_type(ovf_file):
    oss = ovf_file.document.getElementsByTagName("OperatingSystemSection")
    if len(oss) == 0:
        return 'redhat'  # default supported linux
    os_section = oss[0]
    for e in Ovf.getDict(os_section)['children']:
        if e['name'] == u'Description':
            return e['text']
    return 'unknown'


def get_ovf_min_vcpu(ovf_file):
    return _get_ovf_vcpu(ovf_file, "min")


def get_ovf_normal_vcpu(ovf_file):
    return _get_ovf_vcpu(ovf_file, "normal")


def get_ovf_max_vcpu(ovf_file):
    return _get_ovf_vcpu(ovf_file, "max")


def _get_ovf_vcpu(ovf_file, bound):
    """
    Retrieves the number of virtual CPUs to be allocated for the virtual
    machine from the Ovf file.
    """
    vcpu = ''
    virtual_hardware_node = ovf_file.document.getElementsByTagName("VirtualHardwareSection")[0]
    rasd = Ovf.getDict(virtual_hardware_node)['children']
    for resource in rasd:
        if ('rasd:ResourceType' in resource and
                resource['rasd:ResourceType'] == '3'):
            _bound = resource.get('ovf:bound', 'normal')
            if _bound == bound:
                vcpu = resource['rasd:VirtualQuantity']
                break
    return vcpu


def get_networks(ovf_file):
    """
    Retrieves network interface information for the virtual machine from the Ovf file.
    @return: list of dictionaries eg. {interfaceType = 'network', sourceName = 'vmbr0'}
    @rtype: list
    """
    virtual_hardware_node = ovf_file.document.getElementsByTagName("VirtualHardwareSection")[0]
    nets = OvfLibvirt.getOvfNetworks(virtual_hardware_node)
    return nets


def get_openode_features(ovf_file):
    features = []
    try:
        on_dom = ovf_file.document.getElementsByTagName("opennodens:OpenNodeSection")[0]
        feature_dom = on_dom.getElementsByTagName("Features")[0]
        for feature in feature_dom.childNodes:
            if (feature.nodeType == feature.ELEMENT_NODE):
                features.append(str(feature.nodeName))
    except:
        pass
    return features


def get_disks(ovf_file):
    envelope_dom = ovf_file.document.getElementsByTagName("Envelope")[0]
    references_section_dom = envelope_dom.getElementsByTagName("References")[0]
    file_dom_list = references_section_dom.getElementsByTagName("File")
    fileref_dict = {}
    for file_dom in file_dom_list:
        fileref_dict[file_dom.getAttribute("ovf:id")] = file_dom.getAttribute("ovf:href")

    disk_section_dom = envelope_dom.getElementsByTagName("DiskSection")[0]
    disk_dom_list = disk_section_dom.getElementsByTagName("Disk")
    disk_list = []
    for i, disk_dom in enumerate(disk_dom_list):
        disk = {
            "template_name": fileref_dict[disk_dom.getAttribute("ovf:fileRef")],
            "template_format": disk_dom.getAttribute("ovf:format"),
            "deploy_type": "file",
            "type": "file",
            "template_capacity": disk_dom.getAttribute("ovf:capacity"),
            "template_capacity_unit": disk_dom.getAttribute("ovf:capacityAllocationUnits") or "bytes",
            "device": "disk",
            "source_file": fileref_dict[disk_dom.getAttribute("ovf:fileRef")],
            "target_dev": "vd%s" % chr(ord("a") + i),
            "target_bus": "virtio"
        }
        disk_list.append(disk)
    return disk_list


def get_ovf_normal_memory_gb(ovf_file):
    return _get_ovf_memory_gb(ovf_file, "normal")


def get_ovf_max_memory_gb(ovf_file):
    return _get_ovf_memory_gb(ovf_file, "max")


def get_ovf_min_memory_gb(ovf_file):
    return _get_ovf_memory_gb(ovf_file, "min")


def _get_ovf_memory_gb(ovf_file, bound):
    """
    Retrieves the amount of memory (GB) to be allocated for the
    virtual machine from the Ovf file.

    @note: Implementation adopted from module ovf.Ovf
    @note: DSP0004 v2.5.0 outlines the Programmatic Unit forms for
    OVF. This pertains specifically to rasd:AllocationUnits, which accepts
    both the current and deprecated forms. New implementations should not
    use Unit Qualifiers as this form is deprecated.
        - PUnit form, as in "byte * 2^20"
        - PUnit form w/ Units Qualifier(deprecated), as in "MegaBytes"

    @param ovf_file: Ovf template configuration file
    @type ovf_file: OvfFile

    @param bound: memory resource bound: min, max, normal
    @type bound: String

    @return: memory in GB or empty string if no information for the given bound is provided.
    @rtype: String
    """
    memory = ''

    virtual_hardware_node = ovf_file.document.getElementsByTagName("VirtualHardwareSection")[0]
    rasd = Ovf.getDict(virtual_hardware_node)['children']
    for resource in rasd:
        if(resource.has_key('rasd:ResourceType') and
                resource['rasd:ResourceType'] == '4'):
            memoryQuantity = resource['rasd:VirtualQuantity']
            memoryUnits = resource['rasd:AllocationUnits']
            _bound = resource.get('ovf:bound', 'normal')
            if _bound == bound:
                if (memoryUnits.startswith('byte') or
                        memoryUnits.startswith('bit')):
                    # Calculate PUnit numerical factor
                    memoryUnits = memoryUnits.replace('^', '**')

                    # Determine PUnit Quantifier DMTF DSP0004, {byte, bit}
                    # Convert to kilobytes
                    memoryUnits = memoryUnits.split(' ', 1)
                    quantifier = memoryUnits[0]
                    if quantifier not in ['bit', 'byte']:
                        raise ValueError("Incompatible PUnit quantifier for memory.")
                    else:
                        memoryUnits[0] = '2**-10' if quantifier is 'byte' else '2**-13'

                    memoryUnits = ' '.join(memoryUnits)
                    memoryFactor = int(eval(memoryUnits, {}, {}))
                else:
                    if memoryUnits.startswith('Kilo'):
                        memoryFactor = 1024 ** 0
                    elif memoryUnits.startswith('Mega'):
                        memoryFactor = 1024 ** 1
                    elif memoryUnits.startswith('Giga'):
                        memoryFactor = 1024 ** 2
                    else:
                        raise ValueError("Incompatible PUnit quantifier for memory.")

                    if memoryUnits.endswith('Bytes'):
                        memoryFactor *= 1
                    elif memoryUnits.endswith('Bits'):
                        memoryFactor /= 8.0
                    else:
                        raise ValueError("Incompatible PUnit quantifier for memory.")

                memory = str(float(memoryQuantity) * memoryFactor / 1024 ** 2)
                break
    return memory


def save_cpu_mem_to_ovf(ovf_file, settings, ovf_file_name=None):
    """ Save custom memory and cpu settings to ovf file.
    @param ovf_file: ovf.OvfFile object
    @param settings: dict containing new resource values in gigabytes.
    @param ovf_file_name: filename for saving with new name. Optional.
    """
    if ovf_file_name is None:
        ovf_file_name = ovf_file.path

    def _get_child_by_name(node, name):
                for child in node.childNodes:
                    if child.nodeName == name:
                        return child
    items = ovf_file.document.getElementsByTagName('VirtualHardwareSection')
    for item in items:
        for node in item.childNodes:
            if node.nodeName == 'Item':
                res_type = _get_child_by_name(node, 'rasd:ResourceType')
                if res_type.childNodes[0].data == '3':
                    if node.attributes['ovf:bound'].value == 'min':
                        _get_child_by_name(node, 'rasd:VirtualQuantity').childNodes[0].data = settings['vcpu_min']
                    else:
                        _get_child_by_name(node, 'rasd:VirtualQuantity').childNodes[0].data = settings['vcpu']
                if res_type.childNodes[0].data == '4':
                    _get_child_by_name(node, 'rasd:AllocationUnits').childNodes[0].data = 'GigaBytes'
                    if node.attributes['ovf:bound'].value == 'min':
                        _get_child_by_name(node, 'rasd:VirtualQuantity').childNodes[0].data = settings['memory_min']
                    else:
                        _get_child_by_name(node, 'rasd:VirtualQuantity').childNodes[0].data = settings['memory']
    with open(ovf_file_name, 'wt') as f:
        ovf_file.writeFile(f)


def update_referenced_files(ovf_file, template_name, new_name):
    """ Update files in .ovf <Referenced> section.
    @param ovf_file: ovf.OvfFile object
    @param template_name: current template name
    @param new_name: new template name
    """
    VirtualSystem = ovf_file.document.getElementsByTagName('VirtualSystem')
    VirtualSystem[0].attributes['ovf:id'].value = new_name
    References = ovf_file.document.getElementsByTagName('References')
    # TODO: until our packaged templates contain incorrect .ovf
    # we can not rely on files defined in References section
    for ref_node in References:
        file_nodes = ref_node.getElementsByTagName('File')
        for item in file_nodes:
            if item.attributes['ovf:href'].value == template_name + '.tar.gz':
                item.attributes['ovf:href'].value = new_name + '.tar.gz'
    return ovf_file


def generate_ovf_archive_filelist(template_type, ovf_file, template_name, new_name=None):
    """ Generates list of files to add to tar archive
    @param template_type: 'openvz' or 'kvm'
    @param template_name: template name to use
    @param new_name: new base name to use, optional.
    """
    if new_name is None:
        new_name = template_name
    unpacked_base = _get_unpacked_base(template_type)
    filenames = set()

    def suffix_filename_pair(suffix):
        return (os.path.join(unpacked_base, template_name + suffix), new_name + suffix)

    if template_type == 'openvz':
        filenames.add(suffix_filename_pair('.scripts.tar.gz'))
    elif template_type in ('kvm', 'qemu'):
        f, _ = suffix_filename_pair('.img')
        if os.path.exists(f):
            filenames.add(suffix_filename_pair('.img'))

    envelope_dom = ovf_file.document.getElementsByTagName("Envelope")[0]
    references_section_dom = envelope_dom.getElementsByTagName("References")[0]
    file_dom_list = references_section_dom.getElementsByTagName("File")

    for file_dom in file_dom_list:
        filename = file_dom.getAttribute("ovf:href")
        filenames.add((os.path.join(unpacked_base, filename), filename))

    filenames.add(suffix_filename_pair('.ovf'))
    return list(filenames)


def _get_unpacked_base(vm_type):
    """ Get unpacked base for given vm type.
    @param vm_type: 'openvz' or 'kvm'
    """
    return os.path.join(get_config().getstring('general', 'storage-endpoint'),
                        get_config().getstring('general', 'default-storage-pool'),
                        vm_type, 'unpacked')


def get_root_password(ovf_file):
    section = ovf_file.document.getElementsByTagName('opennodens:OpenNodeSection')
    admin_field = section[0].getElementsByTagName('AdminPassword')
    if not admin_field:
        return
    return admin_field[0].firstChild.nodeValue


def get_admin_username(ovf_file):
    section = ovf_file.document.getElementsByTagName('opennodens:OpenNodeSection')
    admin_field = section[0].getElementsByTagName('AdminUsername')
    if not admin_field:
        return
    return admin_field[0].firstChild.nodeValue


def update_template_and_name(vm_type, ovf_file, settings, new_name):
    """ update .ovf and rename template
    @param ovf_file: opened ovf.OvfFile object
    @param settings: dictionary containing settings
    @param new_name: new name for template
    """
    unpacked_base = _get_unpacked_base(vm_type)

    if os.path.exists(os.path.join(unpacked_base, '..', new_name, '.ova')):
        return

    ovf_file = update_referenced_files(ovf_file, settings['template_name'], new_name)
    save_cpu_mem_to_ovf(ovf_file, settings, os.path.join(unpacked_base, new_name + '.ovf'))
    os.unlink(ovf_file.path)

    template_name = settings['template_name']

    def suffix_filename_pair(suffix):
        return (os.path.join(unpacked_base, template_name + suffix),
                os.path.join(unpacked_base, new_name + suffix))

    if vm_type == 'openvz':
        os.rename(suffix_filename_pair('.scripts.tar.gz'))
        os.rename(suffix_filename_pair('.tar.gz'))
    elif vm_type in ('kvm', 'qemu'):
        os.rename(suffix_filename_pair('.img'))

    _package_files(vm_type, ovf_file, template_name, new_name)


def update_template(vm_type, ovf_file, settings):
    """ update .ovf and recreate tar archive
    @param ovf_file: opened ovf.OvfFile object
    @param settings: dictionary containing settings
    """
    save_cpu_mem_to_ovf(ovf_file, settings)
    template = settings['template_name']
    _package_files(vm_type, ovf_file, template)


def _package_files(vm_type, ovf_file, template_name, new_name=None):
    """ Package files to template and calculate hash.
    @param template_name: name of the existing template
    @param new_name: name for new template. Optional
    """
    if new_name is None:
        new_name = template_name
    unpacked_base = _get_unpacked_base(vm_type)

    ## XXX: hack to cleanup templates no matter how they're named
    try:
        os.unlink(os.path.join(unpacked_base, '..', template_name + '.ova'))
        os.unlink(os.path.join(unpacked_base, '..', template_name + '.ova.pfff'))
    except OSError:
        pass

    try:
        os.unlink(os.path.join(unpacked_base, '..', template_name + '.tar'))
        os.unlink(os.path.join(unpacked_base, '..', template_name + '.tar.pfff'))
    except OSError:
        pass

    tmpl_file = os.path.join(unpacked_base, '..', new_name + '.ova')
    filelist = generate_ovf_archive_filelist(vm_type, ovf_file, new_name)
    save_to_tar(tmpl_file, filelist)
    calculate_hash(tmpl_file)
