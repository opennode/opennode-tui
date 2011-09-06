"""Provide OVF to KVM conversion

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

import libvirt

from ovf.OvfFile import OvfFile
from ovf.OvfReferencedFile import OvfReferencedFile
from ovf import Ovf
from ovf import validation
from ovf.commands import cli
from ovf.commands import VERSION_STR  

import opennode.cli.constants as constants
import opennode.cli.kvmcfgproducer as kvmcfgproducer

import tarfile

class OVF2KVM:
    """Convert OVF template to KVM VM"""

    def __init__(self, template_name, vm_name):
        self.ovfFile = None
        self.ovf_xml_dom = None
        self.vm_name = vm_name
        self.template_name = template_name
        self.vh_ident_counter = 1
        self.ovf_template_settings = dict()
        self.ovf_template_settings["template_name"] = string.join(template_name, "")
        self.ovf_template_settings["vm_name"] = string.join(vm_name.split(), "")
        self.ovf_template_settings["domain_type"] = "kvm" 
        self.ovf_template_settings["virt_type"] = "hvm"
        self.ovf_template_settings["memory"] = "0"
        self.ovf_template_settings["min_memory"] = "0"
       	self.ovf_template_settings["max_memory"] = "0"
        self.ovf_template_settings["arch"] = "x86_64"
        self.ovf_template_settings["machine"] = "pc"
        self.ovf_template_settings["vcpu"] = "1"
        self.ovf_template_settings["min_vcpu"] = "1"
        self.ovf_template_settings["max_vcpu"] = "1"
        self.ovf_template_settings["boot_dev"] = "hd"
        self.ovf_template_settings["features"] = []
        self.ovf_template_settings["on_poweroff"] = "destroy"
        self.ovf_template_settings["on_reboot"] = "restart"
        self.ovf_template_settings["on_crash"] = "restart"
        self.ovf_template_settings["clock_offset"] = "utc"
        self.ovf_template_settings["emulator"] = "/usr/libexec/qemu-kvm"
        self.ovf_template_settings["interface"] = {"type" : "bridge", "source_bridge" : "vmbr0"}
        self.ovf_template_settings["serial"] = {"type" : "pty", "target_port" : 0}
        self.ovf_template_settings["console"] = {"type" : "pty", "target_port" : 0}
        self.ovf_template_settings["mouse_bus"] = "ps2"
        self.ovf_template_settings["graphics"] = {"type" : "vnc", "port" : -1, "autoport" : "yes", "keymap" : "et"}
        self.ovf_template_settings["disks"] = []
        self.__getOVFXML()
        self.libvirt_conf_dom = xml.dom.minidom.Document()


    def cleanup(self):
        """
        Clean up system from (partial) template deployment.
        Steps for clean up:
            - delete deployed file based disk images
            - destroy KVM VM in Libvirt if it is already been defined

        @return: True if cleanup was successful
        @rtype: Boolean
        """
        for disk in self.ovf_template_settings["disks"]:
            if (disk["deploy_type"] == "file"):
                try:
                    disk_path = "%s%s-%s" % (constants.FILE_BASED_IMAGE_DIR, self.ovf_template_settings["vm_name"], disk["source_file"])
                    os.remove(disk_path)
                except:
                    pass
        try:
            conn = libvirt.open("qemu:///system")
            conn.undefine(self.ovf_template_settings["vm_name"])
        except:
            pass
        return True


    def unarchiveOVF(self):
        """
        Unarchive OVF template tar archive to template deploy directory

        @return: True if unarchiving OVF template was successful
        @rtype: Boolean
        """
        template_archive_path = "%s%s.tar" % (constants.TEMPLATE_KVM, self.template_name)
        template_path = "%s%s/" % (constants.DEPLOY_TEMPLATE_KVM, self.template_name)
        try:
            template_archive_ts = os.path.getmtime(template_archive_path)
            template_ts = os.path.getmtime(template_path)
            if (template_archive_ts > template_ts):
                template_files = os.listdir("%s" % (template_path))
                for template_file in template_files:
                    os.remove("%s%s" % (template_path, template_file))
                os.rmdir("%s" % (template_path))
       	except:
       	    pass
        template_archive = tarfile.open(template_archive_path, "r")
        template_members = template_archive.getnames()
        for member in template_members:
            try:
                open("%s%s" % (template_path, member), "r")
            except:
                template_archive.extract(member, template_path)
        return True

                                    
    def defineKVMVM(self):
        """
        Define KVM VM using Libvirt API and previously generated Libvirt XML configuration

        @return: True if defining KVM VM was successful   
        @rtype: Boolean
        """
        conn = libvirt.open("qemu:///system")
        conn.defineXML(self.libvirt_conf_dom.toxml())
        return True


    def __getKVMVMList(self):
        """
        Return a list of current KVM VMs (both running and stopped)

        @return: List of KVM VMs on current machine
        @rtype: List
        """
        conn = libvirt.open("qemu:///system")
        name_list = conn.listDefinedDomains();
        name_list2 = []
        id_list = conn.listDomainsID()
        for id in id_list:
            name_list2.append(conn.lookupByID(id).name())
        return name_list + name_list2


    def __getTemplateList(self):
        """
        Return a list of current templates

        @return: List of OVF templates/appliances on OpenNode server
        @rtype: List
        """
        template_list = os.listdir(constants.TEMPLATE_KVM)
       	new_template_list = []
       	for template in	template_list:
       	    if (template.endswith(".tar")):
               	new_template_list.append(template[:-4])
        return new_template_list


    def __getOVFXML(self):
        """
        Return OVF template/appliance XML configuration

        @return: OVF template/appliance XML configuration as DOM Document
        @rtype: DOM Document
        """
        try:
            self.ovfFile = OvfFile("%s%s/%s.ovf" % (constants.DEPLOY_TEMPLATE_KVM, self.template_name, self.template_name))
            self.ovf_xml_dom = xml.dom.minidom.parseString(self.ovfFile.document.toxml())
            return self.ovf_xml_dom
        except:
            raise Exception, "OVF template does not exist"


    def parseOVFXML(self):
        """
        Parse OVF template/appliance XML configuration and save parsed settings

        @return: Parsed OVF template/appliance XML configuration settings
        @rtype: Dictionary
        """
        envelope_dom = self.ovf_xml_dom.getElementsByTagName("Envelope")[0]
        vh_dom = envelope_dom.getElementsByTagName("VirtualHardwareSection")[0]

        try:
            on_dom = envelope_dom.getElementsByTagName("opennodens:OpenNodeSection")[0]
            try:
                feature_dom = on_dom.getElementsByTagName("Features")[0]
                for feature in feature_dom.childNodes:
                    if (feature.nodeType == feature.ELEMENT_NODE):
                        self.ovf_template_settings["features"].append(str(feature.nodeName))
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
        if (not(system_type_list[1] in constants.SYSTEM_ARCHES)):
            raise Exception, "Template architecture is not compatible with KVM on OpenNode server" 
        self.ovf_template_settings["arch"] = system_type_list[1]

        item_dom_list = vh_dom.getElementsByTagName("Item")
        for item_dom in item_dom_list:
            rt_dom = item_dom.getElementsByTagName("rasd:ResourceType")[0]
            if (rt_dom.firstChild.nodeValue == "3"):
                vq_dom = item_dom.getElementsByTagName("rasd:VirtualQuantity")[0]
                bound = "normal"
                if (item_dom.hasAttribute("ovf:bound")):
                    bound = item_dom.getAttribute("ovf:bound")
                if (bound == "min"):
                    self.ovf_template_settings["min_vcpu"] = vq_dom.firstChild.nodeValue
                elif (bound == "max"):
                    self.ovf_template_settings["max_vcpu"] = vq_dom.firstChild.nodeValue
                else:
                    self.ovf_template_settings["vcpu"] = vq_dom.firstChild.nodeValue
            elif (rt_dom.firstChild.nodeValue == "4"):
                vq_dom = item_dom.getElementsByTagName("rasd:VirtualQuantity")[0]
       	       	bound =	"normal"
       	       	if (item_dom.hasAttribute("ovf:bound")):
       	       	    bound = item_dom.getAttribute("ovf:bound")
                if (bound == "min"):
                    self.ovf_template_settings["min_memory"] = str(int(vq_dom.firstChild.nodeValue))
       	       	elif (bound == "max"):
                    self.ovf_template_settings["max_memory"] = str(int(vq_dom.firstChild.nodeValue))
       	       	else:
                    self.ovf_template_settings["memory"] = str(int(vq_dom.firstChild.nodeValue))
            elif (rt_dom.firstChild.nodeValue == "10"):
                vq_dom = item_dom.getElementsByTagName("rasd:Connection")[0]
                self.ovf_template_settings["interface"]["source_bridge"] = vq_dom.firstChild.nodeValue
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
            disk["target_dev"] = "hd%s" % constants.DRIVE_LETTERS[disk_letter_count]
            disk["target_bus"] = "ide"
            disk_list.append(disk)
            disk_letter_count = disk_letter_count + 1
        self.ovf_template_settings["disks"] = disk_list

        self.ovf_template_settings.update(kvmcfgproducer.calculateSystemMinMax(self.ovf_template_settings))

        return self.ovf_template_settings


    def checkDiskSettings(self, ovf_template_settings):
        """
        Check KVM VM disk settings

        @param ovf_template_settings: User updated dictionary of OVF configuration settings
        @type ovf_template_settings: Dictionary

        @return: Dictionary containing error messages for values passed by the user
        @rtype: Dictionary
        """
        errors_dict = dict()
        disk_errors_dict = []
        file_disk_list = []
        lvm_disk_list = []
        physical_disk_list = []
        if ("disks" in ovf_template_settings):
            for disk in ovf_template_settings["disks"]:
                disk_error_dict = dict()
                disk_error_dict["template_name"] = disk["template_name"]
                if (disk["deploy_type"] == "file"):
                    disk_path = "%s%s-%s" % (constants.FILE_BASED_IMAGE_DIR, self.ovf_template_settings["vm_name"], disk["source_file"])
                    if (os.path.isdir(disk_path)):
                        disk_error_dict["error"] = "Disk path is a directory"
                    else:
                        try:
                            open(disk_path, "r")
                            disk_error_dict["error"] = "Disk destination already exists"
                        except:
                            pass
                    if (disk["source_file"] in file_disk_list):
                        disk_error_dict["error"] = "Disk is a duplicate of other disk"
                    file_disk_list.append(disk["source_file"])

                elif (disk["deploy_type"] == "physical"):
                    try:
                        open(disk["source_dev"], "r")
                        disk_error_dict["error"] = "Disk destination already exists"
                    except:
                        pass

                elif (disk["deploy_type"] == "lvm"):
                    try:
                        open(disk["source_dev"], "r")
                        disk_error_dict["error"] = "Disk destination already exists"
                    except:
                        pass
                if (len(disk_error_dict) == 2):
                    disk_errors_dict.append(disk_error_dict)

        if (len(disk_errors_dict) > 0):
            errors_dict["disks"] = disk_errors_dict

        return errors_dict


    def	checkMainSettings(self,	ovf_template_settings):
       	"""
       	Check KVM VM main settings

        @param ovf_template_settings: User updated dictionary of OVF configuration settings
        @type ovf_template_settings: Dictionary

        @return: Dictionary containing error messages for values passed by the user
        @rtype: Dictionary
        """
        errors_dict = dict()
        if ("virt_type" in ovf_template_settings):
            if (not(ovf_template_settings["virt_type"] in constants.KVM_VIRT_TYPES)):
                errors_dict["virt_type"] = "Unknown virtualization type"

        try:
            if ("memory" in ovf_template_settings):
                memory = ovf_template_settings["memory"]
            else:
                memory = self.ovf_template_settings["memory"]
            min_memory = self.ovf_template_settings["min_memory"]
            max_memory = self.ovf_template_settings["max_memory"]
            if (int(memory) < int(min_memory) or int(memory) > int(max_memory)):
                errors_dict["memory"] = "Memory size out of template limits"
        except:
            errors_dict["memory"] = "Memory size has to be integer"

        if ("arch" in ovf_template_settings):
            if (not(ovf_template_settings["arch"] in constants.SYSTEM_ARCHES)):
                errors_dict["arch"] = "Unknown system architecture"

        try:
            if ("vcpu" in ovf_template_settings):
                vcpu = ovf_template_settings["vcpu"]
            else:
                vcpu = self.ovf_template_settings["vcpu"]
            min_vcpu = self.ovf_template_settings["min_vcpu"]
            max_vcpu = self.ovf_template_settings["max_vcpu"]
            if (int(vcpu) < int(min_vcpu) or int(vcpu) > int(max_vcpu)):
                errors_dict["vcpu"] = "Number of virtual CPU's out of template limits"
        except:
            errors_dict["vcpu"] = "Number of virtual CPU's has to be integer"
            
        if ("features" in ovf_template_settings):
            for feature in ovf_template_settings["features"]:
                if (not(feature in constants.KVM_FEATURES)):
                    errors_dict["features"] = "Unknown virtualization feature"

        return errors_dict


    def updateOVFSettings(self, ovf_template_settings):
        """
        User update to OVF configuration settings

        @param ovf_template_settings: User updated dictionary of OVF configuration settings
        @type ovf_template_settings: Dictionary

        @return: Dictionary containing error messages for values passed by the user
        @rtype: Dictionary
        """
        errors_dict = self.checkMainSettings(ovf_template_settings)
        errors_dict.update(self.checkDiskSettings(ovf_template_settings))

        if (len(errors_dict) > 0):
            return errors_dict
        else:
            if ("virt_type" in ovf_template_settings):
                self.ovf_template_settings["virt_type"] = ovf_template_settings["virt_type"]
            if ("memory" in ovf_template_settings):
               	self.ovf_template_settings["memory"] = ovf_template_settings["memory"]
       	    if ("arch" in ovf_template_settings):
                self.ovf_template_settings["arch"] = ovf_template_settings["arch"]
            if ("vcpu" in ovf_template_settings):
                self.ovf_template_settings["vcpu"] = ovf_template_settings["vcpu"]
            if ("features" in ovf_template_settings):
                self.ovf_template_settings["features"] = ovf_template_settings["features"]

            if ("disks" in ovf_template_settings):
                for disk in ovf_template_settings["disks"]:
                    for disk2 in self.ovf_template_settings["disks"]:
                        if (disk["template_name"] == disk2["template_name"]):
                            if (disk["deploy_type"] == "file"):
                                new_disk = dict()
                                new_disk["template_name"] = disk2["template_name"]
       	       	       	       	new_disk["template_format"] = disk2["template_format"]
       	       	       	       	new_disk["template_capacity"] = disk2["template_capacity"]
       	       	       	       	new_disk["deploy_type"] = "file"
                                new_disk["type"] = "block"
       	       	       	       	new_disk["device"] = "disk"
       	       	       	       	new_disk["source_file"] = disk["source_file"]
       	       	       	       	new_disk["target_dev"] = disk["target_dev"]
       	       	       	       	new_disk["target_bus"] = disk["target_bus"]
                                disk2 = new_disk
                                break
       	       	       	    elif (disk["deploy_type"] == "physical"):
       	       	       	       	new_disk = dict()
                                new_disk["template_name"] = disk2["template_name"]
                                new_disk["template_format"] = disk2["template_format"]
                                new_disk["template_capacity"] = disk2["template_capacity"]
                                new_disk["deploy_type"] = "physical"
                                new_disk["type"] = "block"
                                new_disk["device"] = "disk"               
                                new_disk["source_dev"] = disk["source_dev"]
                                new_disk["target_dev"] = disk["target_dev"]
                                new_disk["target_bus"] = disk["target_bus"]
                                disk2 = new_disk
                                break
       	       	       	    elif (disk["deploy_type"] == "lvm"):
       	       	                new_disk = dict()
       	       	       	        new_disk["template_name"] = disk2["template_name"]
       	       	       	        new_disk["template_format"] = disk2["template_format"]
       	       	       	       	new_disk["template_capacity"] = disk2["template_capacity"]
                                new_disk["deploy_type"] = "lvm"
                                new_disk["type"] = "block"
                                new_disk["device"] = "disk"
                                new_disk["source_dev"] = disk["source_dev"]
                                new_disk["target_dev"] = disk["target_dev"]   
                                new_disk["target_bus"] = disk["target_bus"]
                                disk2 = new_disk
                                break
            return dict()


    def testSystem(self):
        """
        Test system compatibility for OVF template/appliance deployment

        @return: True if system is compatible for OVF template/appliance deployment.
        @rtype: Boolean
        """
        if (self.vm_name in self.__getKVMVMList()):
            raise Exception, "KVM VM already exists"
        if (not(self.template_name in self.__getTemplateList())):
            raise Exception, "Template does not exist"
        return True


    def generateKVMLibvirtXML(self):
        """
        Prepare Libvirt XML configuration file from OVF template/appliance.

        @return: Libvirt XML configuration
        @rtype: DOM Document
        """
        self.libvirt_conf_dom = kvmcfgproducer.generateKVMLibvirtXML(self.ovf_template_settings)
        return self.libvirt_conf_dom


    def prepareFileSystem(self):
        """
        Prepare file system for VM template creation in OVF appliance format:
            - create template directory if it does not exist
            - copy disk based images
            - convert block device based images to file based images (ToDo)

        @return: True if file system preparation was successful
        @rtype: Boolean
        """
        for disk in self.ovf_template_settings["disks"]:
            if (disk["deploy_type"] == "file"):
                disk_template_path = "%s%s/%s" % (constants.DEPLOY_TEMPLATE_KVM, self.ovf_template_settings["template_name"], disk["template_name"])
                disk_deploy_path = "%s%s-%s" % (constants.FILE_BASED_IMAGE_DIR, self.ovf_template_settings["vm_name"], disk["source_file"])
                shutil.copy2(disk_template_path, disk_deploy_path)
            elif (disk["deploy_type"] == "physical" or disk["deploy_type"] == "lvm"):
                disk_template_path = "%s%s/%s" % (constants.DEPLOY_TEMPLATE_KVM, self.ovf_template_settings["template_name"], disk["template_name"])
                disk_deploy_path = disk["source_dev"]
                (return_status, return_output) = commands.getstatusoutput("qemu-img convert -f qcow2 -O raw %s %s" % (disk_template_path, disk_deploy_path))
                if (return_status != 0):
                    raise Exception, "Unable to convert VM template file based disks to block-device based disks"
        return True


