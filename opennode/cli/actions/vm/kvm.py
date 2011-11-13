import os
import xml.dom
import shutil
from os import path
import operator

import libvirt

from opennode.cli import config
from opennode.cli.utils import execute
from opennode.cli.actions.vm import ovfutil
from opennode.cli.actions import sysresources as sysres

def get_ovf_template_settings(ovf_file):
    settings = read_default_ovf_settings()
    read_ovf_settings(settings, ovf_file)
    settings["template_name"] = os.path.basename(ovf_file.path)
    return settings
    
def read_default_ovf_settings():
    """ Reads default ovf configuration from file, returns a dictionary of settings."""
    settings = {
        "interface": {"type" : "bridge", "source_bridge" : "vmbr0"},
        "serial": {"type" : "pty", "target_port" : 0},
        "console": {"type" : "pty", "target_port" : 0},
        "graphics": {"type" : "vnc", "port" : -1, "autoport" : "yes", "keymap" : "et"},
        "features": [],
        "disks": []
    }
    settings.update(dict(config.clist('ovf-defaults', 'kvm')))
    if not os.path.exists(settings.get("emulator", "")): 
        settings["emulator"] = "/usr/bin/kvm"
    return settings

def read_ovf_settings(settings, ovf_file):
    """
    Parse OVF template/appliance XML configuration and save parsed settings

    @return: Parsed OVF template/appliance XML configuration settings
    @rtype: Dictionary
    """
    
    sys_type, sys_arch = ovfutil.get_vm_type(ovf_file).split("-")
    if sys_type != "kvm":
        raise Exception, "Given template '%s' is not compatible with KVM on OpenNode server." % sys_type 
    if sys_arch not in ["x86_64", "i686"]:
        raise Exception, "Template architecture '%s' is not compatible with KVM on OpenNode server." % sys_arch
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
    
    networks = ovfutil.get_networks(ovf_file)
    if networks:
        settings["interface"]["source_bridge"] = networks[0]["sourceName"] 
    
    settings["disks"] = ovfutil.get_disks(ovf_file)
    settings["features"] = ovfutil.get_openode_features(ovf_file)

def deploy(settings):
    print "Copying KVM template disks (this may take a while)"
    prepare_file_system(settings)

    print "Generating KVM VM configuration"
    libvirt_conf_dom = generate_libvirt_conf(settings)

    print "Finalyzing KVM template deployment"
    conn = libvirt.open("qemu:///system")
    conn.defineXML(libvirt_conf_dom.toxml())

def prepare_file_system(settings):
    """
    Prepare file system for VM template creation in OVF appliance format:
        - create template directory if it does not exist
            - copy disk based images
        - convert block device based images to file based images (ToDo)
    """
    for disk in settings["disks"]:
        disk_template_path = path.join(config.c("general", "storage-endpoint"),
                                       config.c("general", "default-storage-pool"),
                                       "kvm", "unpacked", disk["template_name"])
        if disk["deploy_type"] == "file":
            disk_deploy_path = path.join(config.c("general", "storage-endpoint"), 
                                         config.c("general", "default-storage-pool"),
                                         "images",  settings["vm_type"] + "-" + disk["source_file"])
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
    name_value = libvirt_conf_dom.createTextNode(settings["vm_type"])
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
        if (disk["deploy_type"] == "file"):
            #File based disk
            disk_dom = libvirt_conf_dom.createElement("disk")
            disk_dom.setAttribute("type", disk["type"])
            disk_dom.setAttribute("device", disk["device"])
            devices_dom.appendChild(disk_dom)
            disk_source_dom = libvirt_conf_dom.createElement("source")
            disk_source_dom.setAttribute("file", path.join(config.c("general", "kvm-images"),
                                                           "%s-%s" % (settings["vm_type"], disk["source_file"])))
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