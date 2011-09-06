"""Provide OpenVZ to OVF conversion"""

import os
import commands
import shutil

import string
import libvirt

from ovf.OvfFile import OvfFile
from ovf.OvfReferencedFile import OvfReferencedFile

import opennode.cli.constants as constants
import opennode.cli.openvzcfgproducer as openvzcfgproducer

import tarfile

class Openvz2OVF:
    """Convert OpenVZ CT to OVF"""

    def __init__(self, vm_id, template_name):
        self.ovfFile = OvfFile()
        self.ovfFile.createEnvelope()
        self.vm_id = string.join(vm_id.split(), "")
        self.template_name = string.join(template_name.split(), "")
        self.vh_ident_counter = 1
        self.openvz_configuration = None
        self.__getOpenvzConf()
        self.ovf_template_settings = dict()
        self.ovf_template_settings["template_name"] = template_name
        self.ovf_template_settings["vm_id"] = vm_id
        self.ovf_template_settings["domain_type"] = "openvz"
        self.ovf_template_settings["memory"] = str(constants.OPENVZ_DEFAULT_MEMORY)
        self.ovf_template_settings["min_memory"] = str(constants.OPENVZ_DEFAULT_MEMORY)
        self.ovf_template_settings["vcpu"] = str(constants.OPENVZ_DEFAULT_VCPU)
        self.ovf_template_settings["min_vcpu"] = str(constants.OPENVZ_DEFAULT_VCPU)

        try:
            os.makedirs("%s" % (constants.DEPLOY_TEMPLATE_OPENVZ))
        except:
            pass


    def	cleanup(self):
       	"""
       	Clean up system	from (partial) template	deployment.
       	Steps for clean	up:
       	    - delete deployed file based disk images
       	    - destroy  OpenVZ CT if if it is already been defined
       	"""
        try:
       	    shutil.rmtree("%s%s/" % (constants.DEPLOY_TEMPLATE_OPENVZ, self.template_name))
        except:
            pass

        try:
            os.remove("%s%s.tar" % (constants.TEMPLATE_OPENVZ, self.template_name))
            os.remove("%s%s.tar.gz" % (constants.ORIGINAL_TEMPLATE_OPENVZ, self.template_name))
            os.remove("%s%s.tar.pfff" % (constants.TEMPLATE_OPENVZ, self.template_name))
            os.remove("%s%s.tar.md5" % (constants.TEMPLATE_OPENVZ, self.template_name))
        except:
            pass


    def __getTemplateList(self):
        """
        Return a list of current templates.

        @return: List of OpenVZ templates on current OpenNode server
        @rtype: List
        """
        template_list = os.listdir(constants.TEMPLATE_OPENVZ)
        new_template_list = []
        for template in template_list:
            if (template.endswith(".tar")):
                new_template_list.append(template[:-4])
        return new_template_list


    def __getOpenvzCTIdList(self):
        """
	Return a list of current OpenVZ CTs (both running and stopped)

        @return: List of OpenVZ CTs on current machine
        @rtype: List
        """
	conn = libvirt.open("openvz:///system")
        id_list = conn.listDefinedDomains();
        id_list2 = conn.listDomainsID()
        id_list3 = []
        for id in id_list:
            id_list3.append(int(id))
        for id in id_list2:
            id_list3.append(int(id))
        return id_list3


    def __getOpenvzConf(self):
        """
        Return OpenVZ CT configuration

        @return: OpenVZ CT configuration
        @rtype: String
        """
        fp = open("%s%s.conf" % (constants.INSTALL_CONFIG_OPENVZ, self.vm_id))
        self.openvz_configuration = fp.read()
        fp.close()


    def testSystem(self):
        """
        Test system compatibility for OVF template/appliance creation

        @return: System compatibility for OVF template/appliance creation
        @rtype: Boolean
        """
	if (self.template_name in self.__getTemplateList()):
            raise Exception, "Template exists"

        if (not(int(self.vm_id) in self.__getOpenvzCTIdList())):
            raise Exception, "OpenVZ CT does not exist"
        return True


    def parseOpenvzConfiguration(self):
        """
        Parse OpenVZ CT configuration to self.ovf_template_settings dictionary.
        This dictionary is later used to create OVF compliant template.

        @return: Parsed OpenVZ CT settings in a dictionary
        @rtype: Dictionary
        """
        openvz_configuration = self.openvz_configuration
        self.ovf_template_settings.update(openvzcfgproducer.parseOpenvzSettings(openvz_configuration))
        return self.ovf_template_settings


    def checkMainSettings(self, ovf_template_settings):
        """
        Check OpenVZ CT main settings
            
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

        return errors_dict


    def updateOpenvzSettings(self, ovf_template_settings):
        """
        Enable user to update OpenVZ CT settings to be used for OVF compliant template creation.
        
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
            return dict()


    def __writeOpenVZOVFXML(self):
        """
        Write OVF XML configuration prepared bu the __generateOpenvzOVFXML() method to a file.

        @return: OpenVZ CT configuration in OVF standard
        @rtype: DOM Document
        """
        file_ptr = open("%s%s/%s.ovf" % (constants.DEPLOY_TEMPLATE_OPENVZ, self.template_name, self.template_name), "w")
        self.ovfFile.writeFile(file_ptr)
        return self.ovfFile.document


    def generateOpenvzOVFXML(self):
        """
        Prepare OVF XML configuration file from OpenVZ CT configuration.

	@return: OpenVZ CT configuration in OVF standard
        @rtype: DOM Document
        """
        virtual_system = self.ovfFile.createVirtualSystem(self.template_name, "OpenVZ OpenNode template")
        virtual_hardware = self.ovfFile.createVirtualHardwareSection(virtual_system, "virtual_hardware", "Virtual hardware requirements for a virtual machine")
        self.__addSystem(virtual_hardware)
        self.__addVirtualHardwareVirtualCPU(virtual_hardware)
        self.__addVirtualHardwareMemory(virtual_hardware)
        self.__addVirtualHardwareInterface(virtual_hardware)

        self.__addDiskRefereces()

        self.__writeOpenVZOVFXML()

        return self.ovfFile.document


    def archiveOVFTemplate(self):
        """
        Create an archive for OVF template. Add OVF configuration file and disk image files to the archive.

        @return: True if the template archive creation was successful
        @rtype: Boolean
        """
        current_dir = os.getcwd()
        template_archive_path = "%s%s.tar" % (constants.TEMPLATE_OPENVZ, self.template_name)
        template_archive = tarfile.open(template_archive_path, "w")
        template_file_list = os.listdir("%s%s/" % (constants.DEPLOY_TEMPLATE_OPENVZ, self.template_name))
        os.chdir("%s%s" % (constants.DEPLOY_TEMPLATE_OPENVZ, self.template_name))
        for template_file in template_file_list:
            template_archive.add(template_file)
        os.chdir(current_dir)

        template_archive.close()

        (status, output) = commands.getstatusoutput("cd %s && pfff -k 6996807 -B %s.tar > %s.tar.pfff" % (constants.TEMPLATE_OPENVZ, self.template_name, self.template_name))
        #(status, output) = commands.getstatusoutput("cd %s && md5sum %s.tar > %s.tar.md5" % (constants.TEMPLATE_OPENVZ, self.template_name, self.template_name))
       	if (status != 0):
       	    raise Exception, "Unable to create template archive"

        return True


    def prepareFileSystem(self):
        """
        Prepare file system for CT template creation in OVF appliance format:
            - create template directory if it does not exist
            - archive and copy OpenVZ CT file system

	@return: True if file system preparation was successful
        @rtype: Boolean
        """
        try:
            os.makedirs("%s%s" % (constants.DEPLOY_TEMPLATE_OPENVZ, self.template_name))        
        except:
            pass

        self.__prepareCTFileSystem()
        
        return True


    def __prepareCTFileSystem(self):
        """
        Prepare OpenVZ CT file system for OVF appliance creation. 
        File system will be archived and copied to OpenVZ template directory

	@return: 0 if preparing VM disks was successful
        @rtype: Integer
        """
        file_system_path = "%s%s/" % (constants.INSTALL_TEMPLATE_OPENVZ, self.vm_id)
        file_system_archive_path = "%s%s/%s.tar.gz" % (constants.DEPLOY_TEMPLATE_OPENVZ, self.template_name, self.template_name)
        
        (status, output) = commands.getstatusoutput("cd %s && tar -cvzpf %s *" % (file_system_path, file_system_archive_path))
        if (status != 0):
            raise Exception, "Unable to archive OpenVZ CT file system"

        commands.getoutput("ln -s %s %s%s.tar.gz" % (file_system_archive_path, constants.ORIGINAL_TEMPLATE_OPENVZ, self.template_name))

        return 0


    def __addDiskRefereces(self):
        """
        Add references of OpenVZ CT file system archive to OVF file

	@return: OVF Disk section as XML DOM Element
        @rtype: DOM Element
        """
        file_system_path = "%s%s/" % (constants.INSTALL_TEMPLATE_OPENVZ, self.vm_id)
        file_system_archive_path = "%s%s/%s.tar.gz" % (constants.DEPLOY_TEMPLATE_OPENVZ, self.template_name, self.template_name)

        ovf_disk_list = []
        filename = "%s.tar.gz" % (self.template_name)
        new_path = "%s" % (file_system_archive_path)
        file_id = "diskfile1"

        file_size = os.path.getsize(new_path)

        refObj = OvfReferencedFile(path=new_path, href=filename, file_id=file_id, size = str(file_size))
        self.ovfFile.addReferencedFile(refObj)

        disk_id = "vmdisk1"

        (status, output) = commands.getstatusoutput("du	-s %s" % (file_system_path))
       	if (status != 0):
       	    raise Exception, "Creation of disk references failed"
       	
        disk_capacity = int(output.split()[0])*1024

        ovf_disk = {}
        ovf_disk["diskId"] = disk_id
        ovf_disk["fileRef"] = file_id
        ovf_disk["capacity"] = str(disk_capacity)
        ovf_disk["populatedSize"] = None
        ovf_disk["format"] = "tar.gz"
        ovf_disk["capacityAllocUnits"] = None
        ovf_disk["parentRef"] = None
        ovf_disk_list.append(ovf_disk)

        self.ovfFile.createReferences()
        return self.ovfFile.createDiskSection(ovf_disk_list, "OpenVZ CT template disks")


    def __addNetworkSection(self):
       	"""
       	Add network section to OVF file
                    
        @return: OVF Network section as XML DOM Element     
        @rtype: DOM Element 
       	"""
        pass


    def __addSystem(self, vh_node):
        """
        Add System section to Virtual Hardware section

        @param vh_node: Virtual Hardware section
        @type vh_node: Node

        @return: OVF System section as XML DOM Element
        @rtype: DOM Element
        """
        return self.ovfFile.createSystem(vh_node, "Virtual Hardware Family", "0", {"VirtualSystemType" : ("%s" % (self.ovf_template_settings["domain_type"]))})


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
        pass

