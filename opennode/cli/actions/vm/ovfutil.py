""" 
@note: open-ovf api: http://gitorious.org/open-ovf/
"""

import os
import warnings
import tarfile
from hashlib import sha1
from datetime import datetime
from os import path

from ovf import Ovf, OvfLibvirt
from ovf.OvfReferencedFile import OvfReferencedFile
from ovf.OvfFile import OvfFile

from opennode.cli import config
from contextlib import closing
from opennode.cli.utils import execute

def get_vm_type(ovf_file):
    return ovf_file.document.getElementsByTagName("vssd:VirtualSystemType")[0].firstChild.nodeValue

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
        disk = dict()
        disk["template_name"] = fileref_dict[disk_dom.getAttribute("ovf:fileRef")]
        disk["template_format"] = disk_dom.getAttribute("ovf:format")
        disk["template_capacity"] = str(int(disk_dom.getAttribute("ovf:capacity"))/1024)
        disk["deploy_type"] = "file"
        disk["type"] = "file"
        disk["device"] = "disk"
        disk["source_file"] = fileref_dict[disk_dom.getAttribute("ovf:fileRef")]
        disk["target_dev"] = "hd%s" % chr(ord("a") + i)
        disk["target_bus"] = "ide"
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
                    # XXX: throwing warning in a CLI is not the best idea
                    #warnings.warn("DSP0004 v2.5.0: use PUnit Qualifiers", DeprecationWarning)

                memory = str(float(memoryQuantity) * memoryFactor / 1024 ** 2)
                break
    return memory

def save_as_ovf(vm_type, vm_settings, ctid, storage_pool, new_tmpl_name):
    """
    Creates ovf template archive for the specified container. 
    Steps:
        - archive container directory
        - generate ovf configuration file
        - pack ovf and container arhive into tar.gz file  
    """
    dest_dir = path.join(config.c('general', 'storage-endpoint'), storage_pool, vm_type)
    unpacked_dir = path.join(dest_dir, "unpacked")
    ct_archive_fnm = path.join(unpacked_dir, "%s.tar.gz" % new_tmpl_name)
    ct_source_dir = path.join("/vz/private", str(ctid))
    
    # Pack vm container catalog
    print "Archiving vm container catalog %s. This may take a while..." % ct_source_dir
    with closing(tarfile.open(ct_archive_fnm, "w:gz")) as tar:
        for file in os.listdir(ct_source_dir):
            tar.add(path.join(ct_source_dir, file), arcname=file)
    
    # generate and save ovf configuration file
    print "Generating ovf file..."
    ovf = generate_ovf_file(vm_type, ctid, vm_settings, new_tmpl_name, ct_archive_fnm)
    ovf_fnm = path.join(unpacked_dir, "%s.ovf" % new_tmpl_name)
    with open(ovf_fnm, 'w') as f:
        ovf.writeFile(f, pretty=True, encoding='UTF-8')
    
    # pack container archive and ovf file
    print "Archiving..."
    ovf_archive_fnm = path.join(dest_dir, "%s.tar" % new_tmpl_name)
    with closing(tarfile.open(ovf_archive_fnm, "w")) as tar:
        tar.add(ct_archive_fnm, arcname=path.basename(ct_archive_fnm))
        tar.add(ovf_fnm, arcname=path.basename(ovf_fnm))
        
    print "Done! Saved template to %s" % ovf_archive_fnm
    
def generate_ovf_file(vm_type, ctid, vm_settings, template_name, ct_archive_fnm):
    ovf = OvfFile()
    ovf.createEnvelope()
    instanceId = 0
    virtualSystem = ovf.createVirtualSystem(ident=template_name, 
                                            info="%s OpenNode template" % vm_type.title())
    hardwareSection = ovf.createVirtualHardwareSection(node=virtualSystem, 
                                ident="virtual_hadrware", 
                                info="Virtual hardware requirements for a virtual machine")
    ovf.createSystem(hardwareSection, "Virtual Hardware Family", str(instanceId), 
                     {"VirtualSystemType": vm_type.lower()})
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
            memory_mb = str(int(round(float(memory) * 1024)))
            ovf.addResourceItem(hardwareSection, {
                "AllocationUnits": "MegaBytes",
                "Caption": "%s MB of memory" % memory_mb,
                "Description": "Memory Size",
                "ElementName": "%s MB of memory" % memory_mb ,
                "InstanceID": str(instanceId),
                "ResourceType": "4",
                "VirtualQuantity": memory_mb
                }, bound=bound)
            instanceId += 1
    
    def get_checksum(fnm):
        # calculate checksum for the file 
        chunk_size = 1024 ** 2 # 1Mb 
        sha = sha1()
        with open(fnm) as file:
            while 1:
                data = file.read(chunk_size)
                if not data:
                    break
                sha.update(data)
        return sha.hexdigest()
    
    # add reference a file (see http://gitorious.org/open-ovf/mainline/blobs/master/py/ovf/OvfReferencedFile.py)
    ref_file = OvfReferencedFile(path.dirname(ct_archive_fnm), 
                                 path.basename("%s.tar.gz" % template_name), 
                                 file_id="diskfile1",
                                 size=str(path.getsize(ct_archive_fnm)),
                                 compression="gz",
                                 checksum=get_checksum(ct_archive_fnm))
    ovf.addReferencedFile(ref_file)
    ovf.createReferences()
    
    def get_ct_disk_usage(ctid):
        return str(round(float(execute("du -s /vz/private/%s/" % ctid).split()[0]) / 1024 ** 2, 3)) # in GB
    
    # add disk section
    ovf.createDiskSection([{
        "diskId": "vmdisk1", 
        "capacity": vm_settings["disk"],
        "populatedSize": get_ct_disk_usage(ctid),
        "capacityAllocUnits": "GigaBytes",
        "fileRef": "diskfile1",
        "parentRef": None,
        "format": "tar.gz"}],
        "%s CT template disks" % vm_type.title())
    
    return ovf 
