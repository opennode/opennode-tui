import os
import xml.dom
import shutil
from os import path
import operator
import tarfile
from contextlib import closing

import libvirt
from ovf.OvfFile import OvfFile
from ovf.OvfReferencedFile import OvfReferencedFile

from opennode.cli import config
from opennode.cli.actions.utils import execute, get_file_size_bytes, calculate_hash
from opennode.cli.actions.vm import ovfutil
from opennode.cli.actions import sysresources as sysres

def get_ovf_template_settings(ovf_file):
    """ Parses ovf file and creates a dictionary of settings """
    settings = read_default_ovf_settings()
    read_ovf_settings(settings, ovf_file)
    settings["template_name"] = path.basename(ovf_file.path)
    return settings

def get_active_template_settings(vm_name, storage_pool):
    """ Reads libvirt configuration of the specified kvm instance """
    settings = read_default_ovf_settings()

    kvm_xml_dom = get_libvirt_conf_xml(vm_name)
    domain_dom = kvm_xml_dom.getElementsByTagName("domain")[0]
    interface_list_dom = domain_dom.getElementsByTagName("interface")

    os_dom = domain_dom.getElementsByTagName("os")[0]
    os_type_dom = os_dom.getElementsByTagName("type")[0]
    os_arch = os_type_dom.getAttribute("arch")
    settings["arch"] = os_arch

    vcpu_count = domain_dom.getElementsByTagName("vcpu")[0].firstChild.nodeValue
    settings["vcpu"] = vcpu_count
    settings["min_vcpu"] = vcpu_count
    settings["max_vcpu"] = vcpu_count

    memory_count = domain_dom.getElementsByTagName("memory")[0].firstChild.nodeValue
    settings["memory"] = str(round(float(memory_count) / 1024 ** 2, 3)) # memory in Gb
    settings["min_memory"] = str(round(float(memory_count) / 1024 ** 2, 3))
    settings["max_memory"] = str(round(float(memory_count) / 1024 ** 2, 3))

    features_dom_list = domain_dom.getElementsByTagName("features")[0].childNodes
    for feature in features_dom_list:
        if (feature.nodeType == feature.ELEMENT_NODE):
            settings["features"].append(str(feature.nodeName))

    for interface_dom in interface_list_dom:
        if interface_dom.getAttribute("type") == "bridge":
            mac_address = interface_dom.getElementsByTagName("mac")[0].getAttribute("address")
            bridge_name = interface_dom.getElementsByTagName("source")[0].getAttribute("bridge")
            settings["interfaces"].append({"type" : "bridge", "source_bridge" : bridge_name, "mac_address" : mac_address})
    return settings

def get_libvirt_conf_xml(vm_name):
    conn = libvirt.open("qemu:///system")
    vm = conn.lookupByName(vm_name)
    document = xml.dom.minidom.parseString(vm.XMLDesc(0))
    return document

def read_default_ovf_settings():
    """ Reads default ovf configuration from file, returns a dictionary of settings."""
    settings = {
        "serial": {"type" : "pty", "target_port" : 0},
        "console": {"type" : "pty", "target_port" : 0},
        "graphics": {"type" : "vnc", "port" : -1, "autoport" : "yes", "keymap" : "us"},
        "interfaces": [],
        "features": [],
        "disks": []
    }
    settings.update(dict(config.clist('ovf-defaults', 'kvm')))
    if not os.path.exists(settings.get("emulator", "")):
        settings["emulator"] = "/usr/bin/kvm"
    return settings

def read_ovf_settings(settings, ovf_file):
    """
    Parses OVF template/appliance XML configuration and save parsed settings.

    @return: Parsed OVF template/appliance XML configuration settings
    @rtype: Dictionary
    """

    sys_type, sys_arch = ovfutil.get_vm_type(ovf_file).split("-")
    if sys_type != "kvm":
        raise Exception, "The chosen template '%s' cannot run on KVM hypervisor." % sys_type
    if sys_arch not in ["x86_64", "i686"]:
        raise Exception, "Template architecture '%s' is not supported." % sys_arch
    settings["arch"] = sys_arch

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

    network_list = ovfutil.get_networks(ovf_file)
    for network in network_list:
        settings["interfaces"].append({"type" : "bridge", "source_bridge": network["sourceName"]})

    settings["disks"] = ovfutil.get_disks(ovf_file)
    settings["features"] = ovfutil.get_openode_features(ovf_file)
    return settings

def deploy(settings, storage_pool):
    print "Copying KVM template disks (this may take a while)..."
    prepare_file_system(settings, storage_pool)

    print "Generating KVM VM configuration..."
    libvirt_conf_dom = generate_libvirt_conf(settings)

    print "Finalyzing KVM template deployment..."
    conn = libvirt.open("qemu:///system")
    conn.defineXML(libvirt_conf_dom.toxml())
    print "Done!"

def prepare_file_system(settings, storage_pool):
    """
    Prepare file system for VM template creation in OVF appliance format:
        - create template directory if it does not exist
        - copy disk based images
        - convert block device based images to file based images
    """
    images_dir = path.join(config.c("general", "storage-endpoint"),
                           storage_pool, "images")
    target_dir = path.join(config.c("general", "storage-endpoint"),
                           storage_pool, "kvm", "unpacked")
    for disk in settings["disks"]:
        disk_template_path = path.join(target_dir, disk["template_name"])
        if disk["deploy_type"] == "file":
            disk_deploy_path = path.join(images_dir, settings["vm_type"] + "-" + disk["source_file"])
            shutil.copy2(disk_template_path, disk_deploy_path)
        elif disk["deploy_type"] in ["physical", "lvm"]:
            disk_deploy_path = disk["source_dev"]
            execute("qemu-img convert -f qcow2 -O raw %s %s" % (disk_template_path, disk_deploy_path))

def adjust_setting_to_systems_resources(ovf_template_settings):
    """
    Adjusts maximum required resources to match available system resources.
    NB! Minimum bound is not adjusted.
    """
    st = ovf_template_settings
    st["memory_max"] = str(min(sysres.get_ram_size_gb(), float(st.get("memory_max", 10**30))))
    st["memory"] = str(min(float(st["memory"]), float(st["memory_max"])))

    st["vcpu_max"] = str(min(sysres.get_cpu_count(), int(st.get("vcpu_max", 10**10))))
    st["vcpu"] = str(min(int(st["vcpu"]), int(st["vcpu_max"])))

    # Checks if minimum required resources exceed maximum available resources
    errors = []
    if float(st["memory_min"]) > float(st["memory_max"]):
        errors.append("Minimum required memory %sGB exceeds total available memory %sGB" %
                      (st["memory_min"], st["memory_max"]))
    if int(st["vcpu_min"]) > int(st["vcpu_max"]):
        errors.append("Minimum required number of vcpus %s exceeds available number %s." %
                      (st["vcpu_min"], st["vcpu_max"]))
    return errors

def get_available_instances():
    """Return a list of defined KVM VMs"""
    conn = libvirt.open("qemu:///system")
    name_list = conn.listDefinedDomains()
    return dict(zip(name_list, name_list))

def get_all_instances():
    """Return all defined KVM VMs"""
    return get_available_instances()

def generate_libvirt_conf(settings):
    """
    Prepare Libvirt XML configuration file from OVF template/appliance.

    @return: Libvirt XML configuration
    @rtype: DOM Document
    """
    libvirt_conf_dom = xml.dom.minidom.Document()
    domain_dom = libvirt_conf_dom.createElement("domain")
    domain_dom.setAttribute("type", settings["domain_type"])
    libvirt_conf_dom.appendChild(domain_dom)

    name_dom = libvirt_conf_dom.createElement("name")
    name_value = libvirt_conf_dom.createTextNode(settings["hostname"])
    name_dom.appendChild(name_value)
    domain_dom.appendChild(name_dom)

    memory_dom = libvirt_conf_dom.createElement("memory")
    memory_value = libvirt_conf_dom.createTextNode(str(int(float(settings["memory"]) * 1024**2)))  # Gb -> Kb
    memory_dom.appendChild(memory_value)
    domain_dom.appendChild(memory_dom)

    vcpu_dom = libvirt_conf_dom.createElement("vcpu")
    vcpu_value = libvirt_conf_dom.createTextNode(str(settings["vcpu"]))
    vcpu_dom.appendChild(vcpu_value)
    domain_dom.appendChild(vcpu_dom)

    os_dom = libvirt_conf_dom.createElement("os")
    os_type_dom = libvirt_conf_dom.createElement("type")
    os_type_dom.setAttribute("arch", settings["arch"])
    os_type_dom.setAttribute("machine", settings["machine"])
    os_type_value = libvirt_conf_dom.createTextNode(settings["virt_type"])
    os_type_dom.appendChild(os_type_value)
    os_dom.appendChild(os_type_dom)
    os_boot_dom = libvirt_conf_dom.createElement("boot")
    os_boot_dom.setAttribute("dev", settings["boot_dev"])
    os_dom.appendChild(os_boot_dom)
    domain_dom.appendChild(os_dom)

    features_dom = libvirt_conf_dom.createElement("features")
    for feature in settings["features"]:
        feature_dom = libvirt_conf_dom.createElement(feature)
        features_dom.appendChild(feature_dom)
    domain_dom.appendChild(features_dom)

    clock_dom = libvirt_conf_dom.createElement("clock")
    clock_dom.setAttribute("offset", settings["clock_offset"])
    domain_dom.appendChild(clock_dom)

    on_poweroff_dom = libvirt_conf_dom.createElement("on_poweroff")
    on_poweroff_value = libvirt_conf_dom.createTextNode(settings["on_poweroff"])
    on_poweroff_dom.appendChild(on_poweroff_value)
    domain_dom.appendChild(on_poweroff_dom)

    on_reboot_dom = libvirt_conf_dom.createElement("on_reboot")
    on_reboot_value = libvirt_conf_dom.createTextNode(settings["on_reboot"])
    on_reboot_dom.appendChild(on_reboot_value)
    domain_dom.appendChild(on_reboot_dom)

    on_crash_dom = libvirt_conf_dom.createElement("on_crash")
    on_crash_value = libvirt_conf_dom.createTextNode(settings["on_crash"])
    on_crash_dom.appendChild(on_crash_value)
    domain_dom.appendChild(on_crash_dom)

    devices_dom = libvirt_conf_dom.createElement("devices")
    domain_dom.appendChild(devices_dom)
    emulator_dom = libvirt_conf_dom.createElement("emulator")
    emulator_value = libvirt_conf_dom.createTextNode(settings["emulator"])
    emulator_dom.appendChild(emulator_value)
    devices_dom.appendChild(emulator_dom)

    drive_letter_count = 0
    for disk in settings["disks"]:
        if disk["deploy_type"] == "file":
            #File based disk
            disk_dom = libvirt_conf_dom.createElement("disk")
            disk_dom.setAttribute("type", disk["type"])
            disk_dom.setAttribute("device", disk["device"])
            devices_dom.appendChild(disk_dom)
            disk_source_dom = libvirt_conf_dom.createElement("source")
            image_path = path.join(config.c("general", "storage-endpoint"), config.c("general", "default-storage-pool"), "images")
            disk_source_dom.setAttribute("file", path.join(image_path,
                                                           "%s-%s" % (settings["vm_type"], disk["source_file"])))
            disk_dom.appendChild(disk_source_dom)
            disk_target_dom = libvirt_conf_dom.createElement("target")
            disk_target_dom.setAttribute("dev", disk["target_dev"])
            disk_target_dom.setAttribute("bus", disk["target_bus"])
            disk_dom.appendChild(disk_target_dom)
        elif disk["deploy_type"] == "physical":
            #Physical block-device based disk
            disk_dom = libvirt_conf_dom.createElement("disk")
            disk_dom.setAttribute("type", disk["type"])
            disk_dom.setAttribute("device", disk["device"])
            devices_dom.appendChild(disk_dom)
            driver_dom = libvirt_conf_dom.createElement("driver")
            driver_dom.setAttribute("name", "qemu")
            driver_dom.setAttribute("cache", "none")
            devices_dom.appendChild(driver_dom)
            disk_source_dom = libvirt_conf_dom.createElement("source")
            disk_source_dom.setAttribute("dev", disk["source_dev"])
            disk_dom.appendChild(disk_source_dom)
            disk_target_dom = libvirt_conf_dom.createElement("target")
            disk_target_dom.setAttribute("dev", disk["target_dev"])
            disk_target_dom.setAttribute("bus", disk["target_bus"])
            disk_dom.appendChild(disk_target_dom)
        elif (disk["deploy_type"] == "lvm"):
            #LVM block-device based disk
            disk_dom = libvirt_conf_dom.createElement("disk")
            disk_dom.setAttribute("type", disk["type"])
            disk_dom.setAttribute("device", disk["device"])
            devices_dom.appendChild(disk_dom)
            disk_source_dom = libvirt_conf_dom.createElement("source")
            disk_source_dom.setAttribute("dev", disk["source_dev"])
            disk_dom.appendChild(disk_source_dom)
            disk_target_dom = libvirt_conf_dom.createElement("target")
            disk_target_dom.setAttribute("dev", disk["target_dev"])
            disk_target_dom.setAttribute("bus", disk["target_bus"])
            disk_dom.appendChild(disk_target_dom)
        drive_letter_count = drive_letter_count + 1

    for interface in settings["interfaces"]:
        interface_dom = libvirt_conf_dom.createElement("interface")
        interface_dom.setAttribute("type", interface["type"])
        devices_dom.appendChild(interface_dom)
        interface_source_dom = libvirt_conf_dom.createElement("source")
        interface_source_dom.setAttribute("bridge", interface["source_bridge"])
        interface_dom.appendChild(interface_source_dom)

    serial_dom = libvirt_conf_dom.createElement("serial")
    serial_dom.setAttribute("type", settings["serial"]["type"])
    devices_dom.appendChild(serial_dom)
    serial_target_dom = libvirt_conf_dom.createElement("target")
    serial_target_dom.setAttribute("port", str(settings["serial"]["target_port"]))
    serial_dom.appendChild(serial_target_dom)

    console_dom = libvirt_conf_dom.createElement("console")
    console_dom.setAttribute("type", settings["console"]["type"])
    devices_dom.appendChild(console_dom)
    console_target_dom = libvirt_conf_dom.createElement("target")
    console_target_dom.setAttribute("port", str(settings["console"]["target_port"]))
    console_dom.appendChild(console_target_dom)

    input_type_dom = libvirt_conf_dom.createElement("input")
    input_type_dom.setAttribute("type", "mouse")
    input_type_dom.setAttribute("bus", settings["mouse_bus"])
    devices_dom.appendChild(input_type_dom)

    graphics_dom = libvirt_conf_dom.createElement("graphics")
    graphics_dom.setAttribute("type", settings["graphics"]["type"])
    graphics_dom.setAttribute("port", str(settings["graphics"]["port"]))
    graphics_dom.setAttribute("autoport", settings["graphics"]["autoport"])
    graphics_dom.setAttribute("keymap", settings["graphics"]["keymap"])
    devices_dom.appendChild(graphics_dom)

    return libvirt_conf_dom

def save_as_ovf(vm_settings, storage_pool, unpack=True):
    """
    Creates ovf template archive for the specified VM.
    Steps:
        - relocate kvm disk files
        - generate ovf configuration file
        - pack ovf and disk files into tar.gz file
        - (if unpack) leave generated files as unpacked
    """

    target_dir = path.join(config.c('general', 'storage-endpoint'), storage_pool, "kvm")
    if unpack:
        target_dir = path.join(target_dir, 'unpacked')
    # prepare file system
    print "Preparing disks... (This may take a while)"
    vm_settings["disks"] = _prepare_disks(vm_settings, target_dir)

    # generate and save ovf configuration file
    print "Generating ovf file..."
    ovf = _generate_ovf_file(vm_settings)
    ovf_fnm = path.join(target_dir, "%s.ovf" % vm_settings["template_name"])
    with open(ovf_fnm, 'w') as f:
        ovf.writeFile(f, pretty=True, encoding='UTF-8')

    # pack container archive and ovf file
    print "Archiving..."
    arch_location =  path.join(config.c('general', 'storage-endpoint'), storage_pool, "kvm")
    ovf_archive_fnm = path.join(arch_location, "%s.tar" % vm_settings["template_name"])
    with closing(tarfile.open(ovf_archive_fnm, "w")) as tar:
        tar.add(ovf_fnm, arcname=path.basename(ovf_fnm))
        for disk in vm_settings["disks"]:
            tar.add(disk["new_path"], arcname=path.basename(disk["new_path"]))

    # remove generated files
    if not unpack:
        os.remove(ovf_fnm)
        for disk in vm_settings["disks"]:
            os.remove(disk["new_path"])
    
    calculate_hash(ovf_archive_fnm)
    print "Done! Template saved at %s" % ovf_archive_fnm

def _prepare_disks(vm_settings, target_dir):
    """
    Prepare VM disks for OVF appliance creation.
    File based disks will be copied to VM creation directory.
    LVM and block-device based disks will be converted into file based images and copied to creation directory.

    @param target_dir: directory where disks will be copied
    """
    disk_list_dom = get_libvirt_conf_xml(vm_settings["vm_name"])\
                        .getElementsByTagName("domain")[0].getElementsByTagName("disk")
    disk_num, disk_list = 0, []
    for disk_dom in disk_list_dom:
        if disk_dom.getAttribute("device") == "disk":
            disk_num += 1
            source_dom = disk_dom.getElementsByTagName("source")[0]
            filename = "%s%d.img" % (vm_settings["template_name"], disk_num)
            new_path = path.join(target_dir, filename)
            if disk_dom.getAttribute("type") == "file":
                disk_path = source_dom.getAttribute("file")
                shutil.copy2(disk_path, new_path)
            elif disk_dom.getAttribute("type") == "block":
                source_dev = source_dom.getAttribute("dev")
                execute("qemu-img convert -f raw -O qcow2 %s %s" % (source_dev, new_path))
            disk_dict = {
                "file_size" : str(get_file_size_bytes(new_path)),
                "filename" : filename,
                "new_path" : new_path,
                "file_id" : "diskfile%d" % (disk_num),
                "disk_id" : "vmdisk%d.img" % (disk_num),
                "disk_capacity" : str(get_kvm_disk_capacity_bytes(new_path))
            }
            disk_list.append(disk_dict)
    return disk_list

def get_kvm_disk_capacity_bytes(path):
    print "Getting capacity of the kvm disk '%s'" %path
    res = execute("virt-df --csv %s" % (path))
    rows = res.split("\n")[2:]
    capacity = 0
    for row in rows:
        row_elements = row.split(",")
        used, available = int(row_elements[3]), int(row_elements[4])
        capacity += used + available
    return capacity * 1024

def _generate_ovf_file(vm_settings):
    """
    Prepare OVF XML configuration file from Libvirt's KVM xml_dump.

    @return: KVM VM configuration in OVF standard
    @rtype: DOM Document
    """
    ovf = OvfFile()
    ovf.createEnvelope()
    ovf.envelope.setAttribute("xmlns:opennodens","http://opennode.activesys.org/schema/ovf/opennodens/1")

    instanceId = 0
    virtualSystem = ovf.createVirtualSystem(ident=vm_settings["template_name"],
                                            info="KVM OpenNode template")
    hardwareSection = ovf.createVirtualHardwareSection(node=virtualSystem,
                                ident="virtual_hadrware",
                                info="Virtual hardware requirements for a virtual machine")

    # add virtual system
    ovf.createSystem(hardwareSection, "Virtual Hardware Family", str(instanceId),
                     {"VirtualSystemType": "%s-%s" % (vm_settings["domain_type"], vm_settings["arch"])})
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

    # add network interfaces
    network_list = []
    for interface in vm_settings["interfaces"]:
        if interface["type"] == "bridge":
            ovf.addResourceItem(hardwareSection, {
                "Address": interface["mac_address"],
                "AutomaticAllocation": "true",
                "Caption": "Ethernet adapter on '%s'" % interface["source_bridge"],
                "Connection": interface["source_bridge"],
                "Description": "Network interface",
                "ElementName": "Ethernet adapter on '%s'" % interface["source_bridge"],
                "InstanceID": "%d" % instanceId,
                "ResourceSubType": "E1000",
                "ResourceType": "10",
            })
            network_list.append({
                "networkID": interface["source_bridge"],
                "networkName": interface["source_bridge"],
                "description": "Network for OVF appliance"
            })
            instanceId += 1
    ovf.createNetworkSection(network_list, "Network for OVF appliance")

    # add references of KVM VM disks (see http://gitorious.org/open-ovf/mainline/blobs/master/py/ovf/OvfReferencedFile.py)
    ovf_disk_list = []
    for disk in vm_settings["disks"]:
        ref_file = OvfReferencedFile(path=disk["new_path"], href=disk["filename"],
                                     file_id=disk["file_id"], size = disk["file_size"])
        ovf.addReferencedFile(ref_file)
        ovf_disk_list.append({
            "diskId": disk["disk_id"],
            "fileRef": disk["file_id"],
            "capacity": str(disk["disk_capacity"]),
            "format": "qcow2",
            "parentRef": None,
            "populatedSize": None,
            "capacityAllocUnits": None
        })
    ovf.createReferences()
    ovf.createDiskSection(ovf_disk_list, "KVM VM template disks")

    # Add OpenNode section to Virtual System node
    doc = xml.dom.minidom.Document()
    on_section = doc.createElement("opennodens:OpenNodeSection")
    on_section.setAttribute("ovf:required","false")
    virtualSystem.appendChild(on_section)

    info_dom = doc.createElement("Info")
    on_section.appendChild(info_dom)
    info_value = doc.createTextNode("OpenNode Section for template customization")
    info_dom.appendChild(info_value)

    features_dom = doc.createElement("Features")
    on_section.appendChild(features_dom)

    for feature in vm_settings["features"]:
        feature_dom = doc.createElement(feature)
        features_dom.appendChild(feature_dom)
    return ovf
