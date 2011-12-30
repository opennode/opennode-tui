""" 
@note: open-ovf api: http://gitorious.org/open-ovf/
"""

from ovf import Ovf, OvfLibvirt

def get_vm_type(ovf_file):
    return ovf_file.document.getElementsByTagName("vssd:VirtualSystemType")[0].firstChild.nodeValue

def get_ovf_os_type(ovf_file):
    os_section = ovf_file.document.getElementsByTagName("OperatingSystemSection")[0]
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
        if (resource.has_key('rasd:ResourceType') and
                resource['rasd:ResourceType'] == '3'):
            _bound = resource.get('attr', {}).get('bound', 'normal')
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
            "target_dev": "hd%s" % chr(ord("a") + i),
            "target_bus": "ide"
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
            _bound = resource.get('attr', {}).get('bound', 'normal')
            if _bound == bound:
                if (memoryUnits.startswith('byte') or
                        memoryUnits.startswith('bit')):
                    # Calculate PUnit numerical factor
                    memoryUnits = memoryUnits.replace('^','**')
                    
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
                        memoryFactor = 1024**0
                    elif memoryUnits.startswith('Mega'):
                        memoryFactor = 1024**1
                    elif memoryUnits.startswith('Giga'):
                        memoryFactor = 1024**2
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
