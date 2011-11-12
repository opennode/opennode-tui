# TODO: implement me
import libvirt
import os
import xml.dom
import shutil
from os import path

from opennode.cli import config
from opennode.cli.utils import execute

#DRIVE_LETTERS = [chr(i) for i in xrange(ord("a"), ord("z") + 1)] # ["a", "b", ..., "z"]
DRIVE_LETTERS = ["a", "b", "z"]
SYSTEM_ARCHES = ["x86_64", "i686"]

def get_ovf_template_settings(ovf_file):
    settings = read_default_ovf_settings()
    ovf_settings = read_ovf_settings(ovf_file)
    settings.update(ovf_settings)
    settings["template_name"] = os.path.basename(ovf_file.path)
    return settings
    
def read_default_ovf_settings():
    """ Reads default ovf configuration from file, returns a dictionary of settings."""
    st = dict(config.clist('ovf-defaults', 'kvm'))
    if not os.path.exists(st["emulator"]): st["emulator"] = "/usr/bin/kvm"
    st["interface"] = {"type" : "bridge", "source_bridge" : "vmbr0"}
    st["serial"] = {"type" : "pty", "target_port" : 0}
    st["console"] = {"type" : "pty", "target_port" : 0}
    st["graphics"] = {"type" : "vnc", "port" : -1, "autoport" : "yes", "keymap" : "et"}
    st["features"] = []
    st["disks"] = []
    return st

def read_ovf_settings(ovf_file):
    """
    Parse OVF template/appliance XML configuration and save parsed settings

    @return: Parsed OVF template/appliance XML configuration settings
    @rtype: Dictionary
    """
    # TODO: check if we can do better with open-ovf library
    ovf_dom = xml.dom.minidom.parseString(ovf_file.document.toxml())
    envelope_dom = ovf_dom.getElementsByTagName("Envelope")[0]
    vh_dom = envelope_dom.getElementsByTagName("VirtualHardwareSection")[0]
    
    st = {}

    try:
        on_dom = envelope_dom.getElementsByTagName("opennodens:OpenNodeSection")[0]
        try:
            feature_dom = on_dom.getElementsByTagName("Features")[0]
            for feature in feature_dom.childNodes:
                if (feature.nodeType == feature.ELEMENT_NODE):
                    st["features"].append(str(feature.nodeName))
        except:
            pass
    except:
        pass

    system_dom = vh_dom.getElementsByTagName("System")[0]
    system_type_dom = system_dom.getElementsByTagName("vssd:VirtualSystemType")[0]
    system_type = system_type_dom.firstChild.nodeValue
    system_type_list = system_type.rsplit("-")
    if ((len(system_type_list) != 2) or (system_type_list[0] != "kvm")):
        raise Exception, "Given template is not compatible with KVM on OpenNode server"
    if (not(system_type_list[1] in SYSTEM_ARCHES)):
        raise Exception, "Template architecture is not compatible with KVM on OpenNode server" 
    st["arch"] = system_type_list[1]

    item_dom_list = vh_dom.getElementsByTagName("Item")
    for item_dom in item_dom_list:
        rt_dom = item_dom.getElementsByTagName("rasd:ResourceType")[0]
        if (rt_dom.firstChild.nodeValue == "3"):
            vq_dom = item_dom.getElementsByTagName("rasd:VirtualQuantity")[0]
            bound = "normal"
            if (item_dom.hasAttribute("ovf:bound")):
                bound = item_dom.getAttribute("ovf:bound")
            if (bound == "min"):
                st["min_vcpu"] = vq_dom.firstChild.nodeValue
            elif (bound == "max"):
                st["max_vcpu"] = vq_dom.firstChild.nodeValue
            else:
                st["vcpu"] = vq_dom.firstChild.nodeValue
        elif (rt_dom.firstChild.nodeValue == "4"):
            vq_dom = item_dom.getElementsByTagName("rasd:VirtualQuantity")[0]
            bound = "normal"
            if (item_dom.hasAttribute("ovf:bound")):
                bound = item_dom.getAttribute("ovf:bound")
            if (bound == "min"):
                st["min_memory"] = str(int(vq_dom.firstChild.nodeValue))
            elif (bound == "max"):
                st["max_memory"] = str(int(vq_dom.firstChild.nodeValue))
            else:
                st["memory"] = str(int(vq_dom.firstChild.nodeValue))
        elif (rt_dom.firstChild.nodeValue == "10"):
            vq_dom = item_dom.getElementsByTagName("rasd:Connection")[0]
            st["interface"]["source_bridge"] = vq_dom.firstChild.nodeValue
    file_references = dict()
    disk_list = []
    
    references_section_dom = envelope_dom.getElementsByTagName("References")[0]
    file_dom_list = references_section_dom.getElementsByTagName("File")
    for file_dom in file_dom_list:
        file_references[file_dom.getAttribute("ovf:id")] = file_dom.getAttribute("ovf:href")
    
    disk_letter_count = 0
    disk_section_dom = envelope_dom.getElementsByTagName("DiskSection")[0]
    disk_dom_list = disk_section_dom.getElementsByTagName("Disk")        
    for disk_dom in disk_dom_list:
        disk = dict()
        disk["template_name"] = file_references[disk_dom.getAttribute("ovf:fileRef")]
        disk["template_format"] = disk_dom.getAttribute("ovf:format")
        disk["template_capacity"] = str(int(disk_dom.getAttribute("ovf:capacity"))/1024)
        disk["deploy_type"] = "file"
        disk["type"] = "file"
        disk["device"] = "disk"
        disk["source_file"] = file_references[disk_dom.getAttribute("ovf:fileRef")]
        disk["target_dev"] = "hd%s" % DRIVE_LETTERS[disk_letter_count]
        disk["target_bus"] = "ide"
        disk_list.append(disk)
        disk_letter_count = disk_letter_count + 1
    st["disks"] = disk_list

    st.update(calculateSystemMinMax(st))

    return st

def calculateSystemMinMax(ovf_template_settings):
    """
    Calculate OpenNode server's system minimum and maximum resource limits:
    
    Values to be calculated:
      - memory min/max size
      - CPU min/max count 
        
    @return: Calculated OpenNode server's system minimum and maximum resource limits
    @rtype: Dictionary
    """
    #CPU count calculation
    output = execute("cat /proc/cpuinfo | grep processor")
    vcpu = str(len(output.split("\n")))
    ovf_template_settings["max_vcpu"] = vcpu
    if (int(ovf_template_settings["min_vcpu"]) > int(vcpu)):
        ovf_template_settings["min_vcpu"] = vcpu

    #Memory size calculation
    output = execute("cat /proc/meminfo | grep MemFree")
    memory_list = output.split()
    try:
        int(memory_list[1])
        memory = str(int(memory_list[1])/1024)
    except:
        raise Exception, "Unable to calculate OpenNode server memory size"
    output = execute("cat /proc/meminfo | grep Buffers")
    memory_list = output.split()
    try:
        int(memory_list[1])
        memory = str(int(memory) + int(memory_list[1])/1024)   
    except:
        raise Exception, "Unable to calculate OpenNode server memory size" 
    output = execute("cat /proc/meminfo | grep Cached")
    memory_list = output.split()
    try:
        int(memory_list[1])
        memory = str(int(memory) + int(memory_list[1])/1024)
    except:
        raise Exception, "Unable to calculate OpenNode server memory size"


    ovf_template_settings["max_memory"] = memory

    if (int(ovf_template_settings["min_memory"]) > int(memory)):
        ovf_template_settings["min_memory"] = memory

    return ovf_template_settings

def generateKVMLibvirtXML(settings):
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
    name_value = libvirt_conf_dom.createTextNode(settings["vm_name"])
    name_dom.appendChild(name_value)
    domain_dom.appendChild(name_dom)
    
    memory_dom = libvirt_conf_dom.createElement("memory")
    memory_value = libvirt_conf_dom.createTextNode(str(int(int(settings["memory"])*1024)))
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
        if (disk["deploy_type"] == "file"):
            #File based disk
            disk_dom = libvirt_conf_dom.createElement("disk")
            disk_dom.setAttribute("type", disk["type"])
            disk_dom.setAttribute("device", disk["device"])
            devices_dom.appendChild(disk_dom)
            disk_source_dom = libvirt_conf_dom.createElement("source")
            disk_source_dom.setAttribute("file", path.join(config("general", "kvm-images"),
                                                           "%s-%s" % (settings["vm_name"], disk["source_file"])))
            disk_dom.appendChild(disk_source_dom)
            disk_target_dom = libvirt_conf_dom.createElement("target")
            disk_target_dom.setAttribute("dev", disk["target_dev"])
            disk_target_dom.setAttribute("bus", disk["target_bus"])
            disk_dom.appendChild(disk_target_dom)
        elif (disk["deploy_type"] == "physical"):
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

    interface_dom = libvirt_conf_dom.createElement("interface")
    interface_dom.setAttribute("type", settings["interface"]["type"])
    devices_dom.appendChild(interface_dom)
    interface_source_dom = libvirt_conf_dom.createElement("source")
    interface_source_dom.setAttribute("bridge", settings["interface"]["source_bridge"])
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

def deploy(settings):
    print "Copying KVM template disks (this may take a while)"
    prepare_file_system(settings)

    print "Generating KVM VM configuration"
    libvirt_conf_dom = generateKVMLibvirtXML(settings)

    print "Finalyzing KVM template deployment"
    conn = libvirt.open("qemu:///system")
    conn.defineXML(libvirt_conf_dom.toxml())

def prepare_file_system(settings):
    """
    Prepare file system for VM template creation in OVF appliance format:
        - create template directory if it does not exist
            - copy disk based images
        - convert block device based images to file based images (ToDo)
    @return: True if file system preparation was successful
    @rtype: Boolean
    """
    for disk in settings["disks"]:
        disk_template_path = path.join(config.c("general", "storage-endpoint"),
                                       config.c("general", "default-storage-pool"),
                                       "kvm", settings["template_name"], disk["template_name"])
        if disk["deploy_type"] == "file":
            disk_deploy_path = path.join(config("general", "kvm-images"), settings["vm_name"] + "-" + disk["source_file"])
            shutil.copy2(disk_template_path, disk_deploy_path)
        elif disk["deploy_type"] in ["physical", "lvm"]:
            disk_deploy_path = disk["source_dev"]
            execute("qemu-img convert -f qcow2 -O raw %s %s" % (disk_template_path, disk_deploy_path))
    return True

def adjust_setting_to_systems_resources(ovf_filename):
    return []
    
def validate_template_settings(template_settings, input_settings):
    raise []

def get_available_instances():
    """Return a list of defined KVM VMs"""
    conn = libvirt.open("qemu:///system")
    name_list = conn.listDefinedDomains();
    vm_dict = dict()
    for name in name_list:
        vm_dict[name] = name
    return vm_dict

def get_template_name(uid):
    """Return a name of the template used for creating specified VM."""
    raise NotImplementedError
