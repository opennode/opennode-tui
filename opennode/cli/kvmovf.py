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

"""Provide KVM to OVF conversion

Copyright 2010, Active Systems
Danel Ahman <danel@active.ee>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""

import os
import xml.dom.minidom
import commands
import shutil
from stat import ST_SIZE
import string

import libvirt

from ovf.OvfFile import OvfFile
from ovf.OvfReferencedFile import OvfReferencedFile

import opennode.cli.constants as constants
import opennode.cli.kvmcfgproducer as kvmcfgproducer

import tarfile

class KVM2OVF:
    """Convert KVM VM to OVF"""

    def __init__(self, vm_name, template_name):
        self.ovfFile = OvfFile()
        self.ovfFile.createEnvelope()
        self.ovfFile.envelope.setAttribute("xmlns:opennodens","http://opennode.activesys.org/schema/ovf/opennodens/1")
        self.vm_name = string.join(vm_name.split(), "")
        self.template_name = string.join(template_name.split(), "")
        self.vh_ident_counter = 1
        self.kvm_xml_dom = None
        self.__getKVMXML()
        self.ovf_template_settings = dict()
        self.ovf_template_settings["template_name"] = template_name
        self.ovf_template_settings["vm_name"] = vm_name
        self.ovf_template_settings["domain_type"] = "kvm"
        self.ovf_template_settings["memory"] = "0"
        self.ovf_template_settings["min_memory"] = "0"
        self.ovf_template_settings["arch"] = "x86_64"
        self.ovf_template_settings["vcpu"] = "1"
        self.ovf_template_settings["min_vcpu"] = "1"
        self.ovf_template_settings["disks"] = []
        self.ovf_template_settings["interfaces"] = []
        self.ovf_template_settings["features"] = []

        try:
    	    os.makedirs("%s" % (constants.DEPLOY_TEMPLATE_KVM))
        except:
            pass

    def	cleanup(self):
       	"""
       	Clean up system	from (partial) template	deployment.
       	Steps for clean	up:
       	    - delete deployed file based disk images
       	    - destroy KVM VM in	Libvirt	if it is already been defined
       	"""
        try:
       	    shutil.rmtree("%s%s/" % (constants.DEPLOY_TEMPLATE_KVM, self.template_name))
        except:
            pass

        try:
            os.remove("%s%s.tar" % (constants.TEMPLATE_KVM, self.template_name))
            os.remove("%s%s.tar.pfff" % (constants.TEMPLATE_KVM, self.template_name))
            os.remove("%s%s.tar.md5" % (constants.TEMPLATE_KVM, self.template_name))
        except:
            pass


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
        Return a list of current templates.

        @return: List of OVF templates on current OpenNode server
        @rtype: List
        """
        template_list = os.listdir(constants.TEMPLATE_KVM)
       	new_template_list = []
       	for template in	template_list:
       	    if (template.endswith(".tar")):
               	new_template_list.append(template[:-4])
        return new_template_list


    def __getKVMXML(self):
        """
        Return Libvirt XML VM configuration

        @return: KVM VM XML configuration
        @rtype: DOM Document
        """
        conn = libvirt.open("qemu:///system")
        vm = conn.lookupByName(self.vm_name)
        self.kvm_xml_dom = xml.dom.minidom.parseString(vm.XMLDesc(0))
        return self.kvm_xml_dom


    def testSystem(self):
        """
        Test system compatibility for OVF template/appliance creation

        @return: System compatibility for OVF template/appliance creation
        @rtype: Boolean
        """
	if (self.template_name in self.__getTemplateList()):
            raise Exception, "Template exists"
        if (not(self.vm_name in self.__getKVMVMList())):
            raise Exception, "KVM VM does not exist"
        return True


    def parseKVMXML(self):
        """
        Parse KVM Libvirt XML configuration to self.ovf_template_settings dictionary.
        This dictionary is later used to create OVF compliant template.

        @return: Parsed KVM VM settings in a dictionary
        @rtype: Dictionary
        """
        self.ovf_template_settings.update(kvmcfgproducer.parseKVMLibvirtXML(self.kvm_xml_dom))
        return self.ovf_template_settings


    def checkMainSettings(self, ovf_template_settings):
        """
	Check KVM VM main settings

        @return: Dictionary containing error messages for values passed by the user
        @rtype: Dictionary
        """
        errors_dict = dict()

        if ("vcpu" in ovf_template_settings):
            vcpu = ovf_template_settings["vcpu"]
        else:
            vcpu = self.ovf_template_settings["vcpu"]
        if ("min_vcpu" in ovf_template_settings):
            min_vcpu = ovf_template_settings["min_vcpu"]
        else:
            min_vcpu = self.ovf_template_settings["min_vcpu"]

        try:
            int(vcpu)
        except:
            errors_dict["vcpu"] = "Number of virtual CPU's has to be integer"
        try:
            int(min_vcpu)
        except:
            errors_dict["vcpu"] = "Minimum number of virtual CPU's has to be integer"
        if (not("vcpu" in errors_dict)):
            if (int(min_vcpu) > int(vcpu)):
                errors_dict["vcpu"] = "Minimun number of virtual CPU's has to be smaller or equal than normal"

        if ("memory" in ovf_template_settings):
            memory = ovf_template_settings["memory"]
        else:
            memory = self.ovf_template_settings["memory"]
        if ("min_memory" in ovf_template_settings):
            min_memory = ovf_template_settings["min_memory"]
        else:
            min_memory = self.ovf_template_settings["min_memory"]

        try:
            int(memory)
        except:
            errors_dict["memory"] = "Memory size has to be integer"
        try:
            int(min_memory)
        except:
            errors_dict["memory"] = "Minimum memory size has to be integer"
        if (not("memory" in errors_dict)):
            if (int(min_memory) > int(memory)):
                errors_dict["memory"] = "Minimun memory size has to be smaller or equal than normal"

        if ("arch" in ovf_template_settings):
            if (not(ovf_template_settings["arch"] in constants.SYSTEM_ARCHES)):
                errors_dict["arch"] = "Unknown system architecture"

        return errors_dict


    def updateKVMSettings(self, ovf_template_settings):
        """
        Enable user to update KVM VM settings to be used for OVF compliant template creation.
        
       	@return: Dictionary containing error messages for values passed	by the user
       	@rtype:	Dictionary
        """
        errors_dict = self.checkMainSettings(ovf_template_settings)

        if (len(errors_dict) > 0):
            return errors_dict
        else:
       	    if ("memory" in ovf_template_settings):
       	        self.ovf_template_settings["memory"] = ovf_template_settings["memory"]
       	    if ("min_memory" in ovf_template_settings):
       	        self.ovf_template_settings["min_memory"] = ovf_template_settings["min_memory"]
       	    if ("vcpu" in ovf_template_settings):
       	        self.ovf_template_settings["vcpu"] = ovf_template_settings["vcpu"]
            if ("min_vcpu" in ovf_template_settings):
                self.ovf_template_settings["min_vcpu"] = ovf_template_settings["min_vcpu"]
            if ("arch" in ovf_template_settings):
                self.ovf_template_settings["arch"] = ovf_template_settings["arch"]
            return dict()


    def __writeKVMOVFXML(self):
        """
        Write OVF XML configuration prepared by the __generateKVMOVFXML() method to a file.

        @return: KVM VM configuration in OVF standard
        @rtype: DOM Document
        """
        file_ptr = open("%s%s/%s.ovf" % (constants.DEPLOY_TEMPLATE_KVM, self.template_name, self.template_name), "w")
        self.ovfFile.writeFile(file_ptr)
        return self.ovfFile.document


    def generateKVMOVFXML(self):
        """
        Prepare OVF XML configuration file from Libvirt's KVM xml_dump.

	@return: KVM VM configuration in OVF standard
        @rtype: DOM Document
        """
        kvm_xml_dom = self.kvm_xml_dom

        domain_dom = kvm_xml_dom.getElementsByTagName("domain")[0]
        disk_list_dom = domain_dom.getElementsByTagName("disk")
        interface_list_dom = domain_dom.getElementsByTagName("interface")

        virtual_system = self.ovfFile.createVirtualSystem(self.template_name, "KVM OpenNode template")
        virtual_hardware = self.ovfFile.createVirtualHardwareSection(virtual_system, "virtual_hardware", "Virtual hardware requirements for a virtual machine")
        self.__addSystem(virtual_hardware)
        self.__addVirtualHardwareVirtualCPU(virtual_hardware)
        self.__addVirtualHardwareMemory(virtual_hardware)
        self.__addVirtualHardwareInterface(virtual_hardware)

        self.__addDiskRefereces()
        self.__addNetworkSection()

        self.__addOpenNodeSection(virtual_system)

        self.__writeKVMOVFXML()

        return self.ovfFile.document


    def archiveOVFTemplate(self):
        """
        Create an archive for OVF template. Add OVF configuration file and disk image files to the archive.

        @return: True if the template archive creation was successful
        @rtype: Boolean
        """
	current_dir = os.getcwd()
        template_archive_path = "%s%s.tar" % (constants.TEMPLATE_KVM, self.template_name)
        template_archive = tarfile.open(template_archive_path, "w")
        template_file_list = os.listdir("%s%s/" % (constants.DEPLOY_TEMPLATE_KVM, self.template_name))
        os.chdir("%s%s" % (constants.DEPLOY_TEMPLATE_KVM, self.template_name))
        for template_file in template_file_list:
            template_archive.add(template_file)
        os.chdir(current_dir)

        template_archive.close()

        (status, output) = commands.getstatusoutput("cd %s && pfff -k 6996807 -B %s.tar > %s.tar.pfff" % (constants.TEMPLATE_KVM, self.template_name, self.template_name))
        #(status, output) = commands.getstatusoutput("cd %s && md5sum %s.tar > %s.tar.md5" % (constants.TEMPLATE_KVM, self.template_name, self.template_name))
        if (status != 0):
            raise Exception, "Unable to create template archive"

        return True


    def prepareFileSystem(self):
        """
        Prepare file system for VM template creation in OVF appliance format:
            - create template directory if it does not exist
            - copy disk based images
            - convert block device based images to file based images (ToDo)

	@return: True if file system preparation was successful
        @rtype: Boolean
        """
        try:
            os.makedirs("%s%s" % (constants.DEPLOY_TEMPLATE_KVM, self.template_name))        
        except:
            pass

        kvm_xml_dom = self.kvm_xml_dom
        domain_dom = kvm_xml_dom.getElementsByTagName("domain")[0]
        disk_list_dom = domain_dom.getElementsByTagName("disk")

        self.__prepareVMDisks(disk_list_dom)
        
        return True


    def __prepareVMDisks(self, disk_list_dom):
        """
        Prepare VM disks for OVF appliance creation. 
        File based disks will be copied to VM creation directory.
        LVM and block-device based disks will be converted into file based images and copied to creation directory.

        @param disk_list_dom: List of disk DOM objects
        @type disk_list_dom: NodeList

	@return: 0 if preparing VM disks was successful
        @rtype: Integer
        """
        i = 1
	ovf_disk_list = []
        for disk_dom in disk_list_dom:
            if (disk_dom.getAttribute("device") == "disk"):
                if (disk_dom.getAttribute("type") == "file"):
                    source_dom = disk_dom.getElementsByTagName("source")[0]
                    disk_path = source_dom.getAttribute("file")
                    filename = "%s%d.img" % (self.template_name, i)
                    new_path = "%s%s/%s" % (constants.DEPLOY_TEMPLATE_KVM,
                                                 self.template_name,
                                                 filename)
                    file_id = "diskfile%d" % (i)
                    disk_id = "vmdisk%d.img" % (i)
                    shutil.copy2(disk_path, new_path)

                    file_size = str(os.stat(new_path)[ST_SIZE])

                    disk_capacity = 0
                    (return_status, return_output) = commands.getstatusoutput("virt-df --csv %s" % (new_path))
                    rows = return_output.split("\n")[2:]
                    for row in rows:
                        row_elements = row.split(",")
                        disk_capacity += 1024 * (int(row_elements[3]) + int(row_elements[4]))

                    disk_dict = {"file_size" : file_size, "filename" : filename, "new_path" : new_path, "file_id" : file_id, "disk_id" : disk_id, "disk_capacity" : str(disk_capacity)}
                    self.ovf_template_settings["disks"].append(disk_dict)
                elif (disk_dom.getAttribute("type") == "block"):
                    source_dom = disk_dom.getElementsByTagName("source")[0]
                    source_dev = source_dom.getAttribute("dev")
                    filename = "%s%d.img" % (self.template_name, i)
                    new_path = "%s%s/%s" % (constants.DEPLOY_TEMPLATE_KVM,
                                                 self.template_name,
                                                 filename)
                    file_id = "diskfile%d" % (i)
                    disk_id = "vmdisk%d.img" % (i)
                    (return_status, return_output) = commands.getstatusoutput("qemu-img convert -f raw -O qcow2 %s %s" % (source_dev, new_path))
                    if (return_status != 0):
                        raise Exception, "Unable to convert block-device based VM disk to file based VM disk"
                    
                    file_size = str(os.stat(new_path)[ST_SIZE])

                    disk_capacity = 0
                    (return_status, return_output) = commands.getstatusoutput("virt-df --csv %s" % (new_path))
                    rows = return_output.split("\n")[2:]
                    for row in rows:
               	        row_elements = row.split(",")
               	        disk_capacity += 1024 * (int(row_elements[3]) + int(row_elements[4]))
                    
                    disk_dict = {"file_size" : file_size, "filename" : filename, "new_path" : new_path, "file_id" : file_id, "disk_id" : disk_id, "disk_capacity" : str(disk_capacity)}
                    self.ovf_template_settings["disks"].append(disk_dict)

            i += 1
        return 0


    def __addDiskRefereces(self):
        """
        Add references of KVM VM disks to OVF file

	@return: OVF Disk section as XML DOM Element
        @rtype: DOM Element
        """
        i = 1
        ovf_disk_list = []
        for disk in self.ovf_template_settings["disks"]:
            filename = disk["filename"]
            new_path = disk["new_path"]
            file_id = disk["file_id"]

            file_size = disk["file_size"]

            refObj = OvfReferencedFile(path=new_path, href=filename, 
                                       file_id=file_id, size = file_size)
            self.ovfFile.addReferencedFile(refObj)

            disk_id = disk["disk_id"]

            disk_capacity = disk["disk_capacity"]

            ovf_disk = {}
            ovf_disk["diskId"] = disk_id
            ovf_disk["fileRef"] = file_id
            ovf_disk["capacity"] = str(disk_capacity)
            ovf_disk["populatedSize"] = None
            ovf_disk["format"] = "qcow2"
            ovf_disk["capacityAllocUnits"] = None
            ovf_disk["parentRef"] = None
            ovf_disk_list.append(ovf_disk)

            i += 1
        self.ovfFile.createReferences()
        return self.ovfFile.createDiskSection(ovf_disk_list, "KVM VM template disks")


    def __addNetworkSection(self):
       	"""
       	Add network section to OVF file
                    
        @return: OVF Network section as XML DOM Element     
        @rtype: DOM Element 
       	"""
        for interface in self.ovf_template_settings["interfaces"]:               
            if (interface["type"] == "bridge"):
                network_name = interface["source_bridge"]

       	        network_list = []
       	        network = {}
                network["networkID"] = network_name
                network["networkName"] = network_name
                network["description"] = "Network for OVF appliance"
                network_list.append(network)
        
        return self.ovfFile.createNetworkSection(network_list, "Network for OVF appliance")


    def __addSystem(self, vh_node):
        """
        Add System section to Virtual Hardware section

        @param vh_node: Virtual Hardware section
        @type vh_node: Node

        @return: OVF System section as XML DOM Element
        @rtype: DOM Element
        """
        return self.ovfFile.createSystem(vh_node, "Virtual Hardware Family", "0", {"VirtualSystemType" : ("%s-%s" % (self.ovf_template_settings["domain_type"], self.ovf_template_settings["arch"]))})


    def __addVirtualHardwareVirtualCPU(self, vh_node):
	"""
        Add virtual CPU item to Virtual Hardware section
                        
        @param vh_node: Virtual Hardware section
        @type vh_node: Node

        @return: OVF Virtual CPU Item as XML DOM Element     
        @rtype: DOM Element 
        """
        vcpu_count = int(self.ovf_template_settings["vcpu"])

        refs_dict = {}
        refs_dict["Address"] = None
        refs_dict["AddressOnParent"] = None
        refs_dict["AllocationUnits"] = None
        refs_dict["AutomaticAllocation"] = None
        refs_dict["AutomaticDeallocation"] = None
        refs_dict["Caption"] = "%d virtual CPU" % (vcpu_count)
        refs_dict["Connection"] = None
        refs_dict["ConsumerVisibility"] = None
        refs_dict["Description"] = "Number of virtual CPUs"
        refs_dict["ElementName"] = "%d virtual CPU" % (vcpu_count)
        refs_dict["HostResource"] = None
        refs_dict["InstanceID"] = "%d" % (self.vh_ident_counter)
        refs_dict["Limit"] = None
        refs_dict["MappingBehavior"] = None
        refs_dict["OtherResourceType"] = None
        refs_dict["Parent"] = None
        refs_dict["PoolID"] = None
        refs_dict["Reservation"] = None
        refs_dict["ResourceSubType"] = None
        refs_dict["ResourceType"] = "3"
        refs_dict["VirtualQuantity"] = "%d" % (vcpu_count)
        refs_dict["Weight"] = None

        self.vh_ident_counter += 1

        self.ovfFile.addResourceItem(node = vh_node, refsDefDict = refs_dict, bound = "normal")

        vcpu_count = int(self.ovf_template_settings["min_vcpu"])
        refs_dict["Caption"] = "%d virtual CPU" % (vcpu_count)
        refs_dict["ElementName"] = "%d virtual CPU" % (vcpu_count)
        refs_dict["InstanceID"] = "%d" % (self.vh_ident_counter)
        refs_dict["VirtualQuantity"] = "%d" % (vcpu_count)
        self.vh_ident_counter += 1
        self.ovfFile.addResourceItem(node = vh_node, refsDefDict = refs_dict, bound = "min")

        return self.vh_ident_counter-1


    def __addVirtualHardwareMemory(self, vh_node):
        """
	Add virtual CPU item to Virtual Hardware section

        @param vh_node: Virtual Hardware section
        @type vh_node: Node

        @return: OVF Virtual Memory Item as XML DOM Element     
        @rtype: DOM Element 
        """
	memory_count = int(self.ovf_template_settings["memory"])

        refs_dict = {}
        refs_dict["Address"] = None
        refs_dict["AddressOnParent"] = None
        refs_dict["AllocationUnits"] = "MegaBytes"
	refs_dict["AutomaticAllocation"] = None
        refs_dict["AutomaticDeallocation"] = None
        refs_dict["Caption"] = "%d MB of memory" % (memory_count)
        refs_dict["Connection"] = None
        refs_dict["ConsumerVisibility"] = None
        refs_dict["Description"] = "Memory Size"
        refs_dict["ElementName"] = "%d MB of memory" % (memory_count)
        refs_dict["HostResource"] = None
        refs_dict["InstanceID"] = "%d" % (self.vh_ident_counter)
        refs_dict["Limit"] = None
        refs_dict["MappingBehavior"] = None
        refs_dict["OtherResourceType"] = None
        refs_dict["Parent"] = None
        refs_dict["PoolID"] = None
        refs_dict["Reservation"] = None
        refs_dict["ResourceSubType"] = None
        refs_dict["ResourceType"] = "4"
        refs_dict["VirtualQuantity"] = "%d" % (memory_count)
        refs_dict["Weight"] = None

        self.vh_ident_counter += 1

        self.ovfFile.addResourceItem(node = vh_node, refsDefDict = refs_dict, bound = "normal")

        memory_count = int(self.ovf_template_settings["min_memory"])
        refs_dict["Caption"] = "%d MB of memory" % (memory_count)
        refs_dict["ElementName"] = "%d MB of memory" % (memory_count)
        refs_dict["InstanceID"] = "%d" % (self.vh_ident_counter)
        refs_dict["VirtualQuantity"] = "%d" % (memory_count)
        self.vh_ident_counter += 1
        self.ovfFile.addResourceItem(node = vh_node, refsDefDict = refs_dict, bound = "min")

        return self.vh_ident_counter-1


    def __addVirtualHardwareInterface(self, vh_node):
        """
	Add network interfaces to Virtual Hardware section

        @param vh_node: Virtual Hardware section
        @type vh_node: Node

        @return: OVF Network Interface Item as XML DOM Element     
        @rtype: DOM Element 
        """
        for interface in self.ovf_template_settings["interfaces"]:
            if (interface["type"] == "bridge"):
                mac_address = interface["mac_address"]
                bridge_name = interface["source_bridge"]

                refs_dict = {}
                refs_dict["Address"] = mac_address
                refs_dict["AddressOnParent"] = None     
                refs_dict["AllocationUnits"] = None
                refs_dict["AutomaticAllocation"] = "true"
                refs_dict["AutomaticDeallocation"] = None
                refs_dict["Caption"] = "Ethernet adapter on '%s'" % (bridge_name)
                refs_dict["Connection"] = bridge_name
                refs_dict["ConsumerVisibility"] = None
                refs_dict["Description"] = "Network interface"
                refs_dict["ElementName"] = "Ethernet adapter on '%s'" % (bridge_name)
                refs_dict["HostResource"] = None
                refs_dict["InstanceID"] = "%d" % (self.vh_ident_counter)
                refs_dict["Limit"] = None
                refs_dict["MappingBehavior"] = None
                refs_dict["OtherResourceType"] = None
                refs_dict["Parent"] = None
                refs_dict["PoolID"] = None
                refs_dict["Reservation"] = None
                refs_dict["ResourceSubType"] = "E1000"
                refs_dict["ResourceType"] = "10"
                refs_dict["VirtualQuantity"] = None
                refs_dict["Weight"] = None

                self.vh_ident_counter += 1

                self.ovfFile.addResourceItem(vh_node, refs_dict)

            return self.vh_ident_counter-1


    def __addOpenNodeSection(self, vs_node):
        """
        Add OpenNode section to Virtual System node
                
        @param vh_node: VirtualSystem section
        @type vh_node: Node
                
        @return: OpenNode section XML DOM Element
        @rtype: DOM Element
        """
        doc = xml.dom.minidom.Document()
        on_section = doc.createElement("opennodens:OpenNodeSection")
        on_section.setAttribute("ovf:required","false")
        vs_node.appendChild(on_section)

        info_dom = doc.createElement("Info")
        on_section.appendChild(info_dom)
        info_value = doc.createTextNode("OpenNode Section for template customization")
        info_dom.appendChild(info_value)
        
        features_dom = doc.createElement("Features")
        on_section.appendChild(features_dom)
        
        for feature in self.ovf_template_settings["features"]:
            feature_dom = doc.createElement(feature)
            features_dom.appendChild(feature_dom)

        return on_section
