#!/usr/bin/python
###########################################################################
#
#    Copyright (C) 2009, 2010, 2011 Active Systems LLC, 
#    url: http://www.active.ee, email: info@active.ee
#
#    This file is part of OpenNode.
#
#    OpenNode is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    OpenNode is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with OpenNode.  If not, see <http://www.gnu.org/licenses/>.
#
###########################################################################

"""Provide KVM Libvirt XML configuration management features

Copyright 2010, Active Systems
Danel Ahman <danel@active.ee>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""

import os
import sys
import xml.dom.minidom
import commands
import shutil
import re
import string
from stat import ST_SIZE

import opennode.cli.constants as constants


def parseKVMLibvirtXML(kvm_xml_dom):
    """
    Parse KVM Libvirt XML configuration to ovf_template_settings dictionary.
    This dictionary is later used to create OVF compliant template.
    
    @return: Parsed KVM VM settings in a dictionary
    @rtype: Dictionary
    """
    ovf_template_settings = dict()
    ovf_template_settings["memory"] = str(constants.KVM_DEFAULT_MEMORY)
    ovf_template_settings["min_memory"] = str(constants.KVM_DEFAULT_MEMORY)
    ovf_template_settings["max_memory"] = str(constants.KVM_DEFAULT_MEMORY)
    ovf_template_settings["arch"] = constants.SYSTEM_ARCHES[0]
    ovf_template_settings["vcpu"] = str(constants.KVM_DEFAULT_VCPU)
    ovf_template_settings["max_vcpu"] = str(constants.KVM_DEFAULT_VCPU)
    ovf_template_settings["min_vcpu"] = str(constants.KVM_DEFAULT_VCPU)
    ovf_template_settings["interfaces"] = []
    ovf_template_settings["features"] = []

    domain_dom = kvm_xml_dom.getElementsByTagName("domain")[0]
    disk_list_dom = domain_dom.getElementsByTagName("disk")
    interface_list_dom = domain_dom.getElementsByTagName("interface")

    os_dom = domain_dom.getElementsByTagName("os")[0]
    os_type_dom = os_dom.getElementsByTagName("type")[0]
    os_arch = os_type_dom.getAttribute("arch")
    ovf_template_settings["arch"] = os_arch

    vcpu_count = domain_dom.getElementsByTagName("vcpu")[0].firstChild.nodeValue
    ovf_template_settings["vcpu"] = vcpu_count
    ovf_template_settings["min_vcpu"] = vcpu_count
    ovf_template_settings["max_vcpu"] = vcpu_count

    memory_count = domain_dom.getElementsByTagName("memory")[0].firstChild.nodeValue
    ovf_template_settings["memory"] = str(int(memory_count)/1024)
    ovf_template_settings["min_memory"] = str(int(memory_count)/1024)
    ovf_template_settings["max_memory"] = str(int(memory_count)/1024)

    features_dom_list = domain_dom.getElementsByTagName("features")[0].childNodes
    for feature in features_dom_list:
        if (feature.nodeType == feature.ELEMENT_NODE):
            ovf_template_settings["features"].append(str(feature.nodeName))

    for interface_dom in interface_list_dom:
        if (interface_dom.getAttribute("type") == "bridge"):
            mac_address = interface_dom.getElementsByTagName("mac")[0].getAttribute("address")
            bridge_name = interface_dom.getElementsByTagName("source")[0].getAttribute("bridge")
            ovf_template_settings["interfaces"].append({"type" : "bridge", "source_bridge" : bridge_name, "mac_address" : mac_address})

    return ovf_template_settings


def generateKVMLibvirtXML(ovf_template_settings):
    """
    Prepare Libvirt XML configuration file from OVF template/appliance.

    @return: Libvirt XML configuration
    @rtype: DOM Document
    """
    libvirt_conf_dom = xml.dom.minidom.Document()
    domain_dom = libvirt_conf_dom.createElement("domain")
    domain_dom.setAttribute("type", ovf_template_settings["domain_type"])
    libvirt_conf_dom.appendChild(domain_dom)

    name_dom = libvirt_conf_dom.createElement("name")
    name_value = libvirt_conf_dom.createTextNode(ovf_template_settings["vm_name"])
    name_dom.appendChild(name_value)
    domain_dom.appendChild(name_dom)

    memory_dom = libvirt_conf_dom.createElement("memory")
    memory_value = libvirt_conf_dom.createTextNode(str(int(int(ovf_template_settings["memory"])*1024)))
    memory_dom.appendChild(memory_value)
    domain_dom.appendChild(memory_dom)

    vcpu_dom = libvirt_conf_dom.createElement("vcpu")
    vcpu_value = libvirt_conf_dom.createTextNode(str(ovf_template_settings["vcpu"]))
    vcpu_dom.appendChild(vcpu_value)
    domain_dom.appendChild(vcpu_dom)

    os_dom = libvirt_conf_dom.createElement("os")
    os_type_dom = libvirt_conf_dom.createElement("type")
    os_type_dom.setAttribute("arch", ovf_template_settings["arch"])
    os_type_dom.setAttribute("machine", ovf_template_settings["machine"])
    os_type_value = libvirt_conf_dom.createTextNode(ovf_template_settings["virt_type"])
    os_type_dom.appendChild(os_type_value)
    os_dom.appendChild(os_type_dom)
    os_boot_dom = libvirt_conf_dom.createElement("boot")
    os_boot_dom.setAttribute("dev", ovf_template_settings["boot_dev"])
    os_dom.appendChild(os_boot_dom)
    domain_dom.appendChild(os_dom)

    features_dom = libvirt_conf_dom.createElement("features")
    for feature in ovf_template_settings["features"]:
        feature_dom = libvirt_conf_dom.createElement(feature)
        features_dom.appendChild(feature_dom)
    domain_dom.appendChild(features_dom)

    clock_dom = libvirt_conf_dom.createElement("clock")
    clock_dom.setAttribute("offset", ovf_template_settings["clock_offset"])
    domain_dom.appendChild(clock_dom)

    on_poweroff_dom = libvirt_conf_dom.createElement("on_poweroff")
    on_poweroff_value = libvirt_conf_dom.createTextNode(ovf_template_settings["on_poweroff"])
    on_poweroff_dom.appendChild(on_poweroff_value)
    domain_dom.appendChild(on_poweroff_dom)
    
    on_reboot_dom = libvirt_conf_dom.createElement("on_reboot")
    on_reboot_value = libvirt_conf_dom.createTextNode(ovf_template_settings["on_reboot"])
    on_reboot_dom.appendChild(on_reboot_value)
    domain_dom.appendChild(on_reboot_dom)

    on_crash_dom = libvirt_conf_dom.createElement("on_crash")
    on_crash_value = libvirt_conf_dom.createTextNode(ovf_template_settings["on_crash"])
    on_crash_dom.appendChild(on_crash_value)
    domain_dom.appendChild(on_crash_dom)

    devices_dom = libvirt_conf_dom.createElement("devices")
    domain_dom.appendChild(devices_dom)
    emulator_dom = libvirt_conf_dom.createElement("emulator")
    emulator_value = libvirt_conf_dom.createTextNode(ovf_template_settings["emulator"])
    emulator_dom.appendChild(emulator_value)
    devices_dom.appendChild(emulator_dom)

    drive_letter_count = 0        
    for disk in ovf_template_settings["disks"]:
        if (disk["deploy_type"] == "file"):
            #File based disk
            disk_dom = libvirt_conf_dom.createElement("disk")
            disk_dom.setAttribute("type", disk["type"])
            disk_dom.setAttribute("device", disk["device"])
            devices_dom.appendChild(disk_dom)
            disk_source_dom = libvirt_conf_dom.createElement("source")
            disk_source_dom.setAttribute("file", "%s%s-%s" % (constants.FILE_BASED_IMAGE_DIR, ovf_template_settings["vm_name"], disk["source_file"]))
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
    interface_dom.setAttribute("type", ovf_template_settings["interface"]["type"])
    devices_dom.appendChild(interface_dom)
    interface_source_dom = libvirt_conf_dom.createElement("source")
    interface_source_dom.setAttribute("bridge", ovf_template_settings["interface"]["source_bridge"])
    interface_dom.appendChild(interface_source_dom)

    serial_dom = libvirt_conf_dom.createElement("serial")
    serial_dom.setAttribute("type", ovf_template_settings["serial"]["type"])
    devices_dom.appendChild(serial_dom)
    serial_target_dom = libvirt_conf_dom.createElement("target")
    serial_target_dom.setAttribute("port", str(ovf_template_settings["serial"]["target_port"]))
    serial_dom.appendChild(serial_target_dom)

    console_dom = libvirt_conf_dom.createElement("console")
    console_dom.setAttribute("type", ovf_template_settings["console"]["type"])
    devices_dom.appendChild(console_dom)
    console_target_dom = libvirt_conf_dom.createElement("target")
    console_target_dom.setAttribute("port", str(ovf_template_settings["console"]["target_port"]))
    console_dom.appendChild(console_target_dom)

    input_type_dom = libvirt_conf_dom.createElement("input")
    input_type_dom.setAttribute("type", "mouse")
    input_type_dom.setAttribute("bus", ovf_template_settings["mouse_bus"])
    devices_dom.appendChild(input_type_dom)        

    graphics_dom = libvirt_conf_dom.createElement("graphics")
    graphics_dom.setAttribute("type", ovf_template_settings["graphics"]["type"])
    graphics_dom.setAttribute("port", str(ovf_template_settings["graphics"]["port"]))
    graphics_dom.setAttribute("autoport", ovf_template_settings["graphics"]["autoport"])
    graphics_dom.setAttribute("keymap", ovf_template_settings["graphics"]["keymap"])
    devices_dom.appendChild(graphics_dom)

    return libvirt_conf_dom


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
    (status, output) = commands.getstatusoutput("cat /proc/cpuinfo | grep processor")
    if (status != 0):
        raise Exception, "Unable to calculate OpenNode server CPU count"
    vcpu = str(len(output.split("\n")))
    ovf_template_settings["max_vcpu"] = vcpu
    if (int(ovf_template_settings["min_vcpu"]) > int(vcpu)):
        ovf_template_settings["min_vcpu"] = vcpu

    #Memory size calculation
    (status, output) = commands.getstatusoutput("cat /proc/meminfo | grep MemFree")
    if (status != 0):
        raise Exception, "Unable to calculate OpenNode server memory size"
    memory_list = output.split()
    try:
        int(memory_list[1])
        memory = str(int(memory_list[1])/1024)
    except:
        raise Exception, "Unable to calculate OpenNode server memory size"
    (status, output) = commands.getstatusoutput("cat /proc/meminfo | grep Buffers")
    if (status != 0):
        raise Exception, "Unable to calculate OpenNode server memory size"
    memory_list = output.split()
    try:
        int(memory_list[1])
        memory = str(int(memory) + int(memory_list[1])/1024)   
    except:
        raise Exception, "Unable to calculate OpenNode server memory size" 
    (status, output) = commands.getstatusoutput("cat /proc/meminfo | grep Cached")
    if (status != 0):
        raise Exception, "Unable to calculate OpenNode server memory size"
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
