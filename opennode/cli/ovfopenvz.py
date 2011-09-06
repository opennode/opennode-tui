"""Provide OVF to OpenVZ conversion"""

import os
import xml.dom.minidom
import commands
import tarfile
import string

import libvirt

from ovf.OvfFile import OvfFile

import opennode.cli.constants as constants
import opennode.cli.vzcfgproducer as vzcfgproducer
import opennode.cli.openvzcfgproducer as openvzcfgproducer

class OVF2Openvz:
    """Convert OVF template to OpenVZ CT"""

    def __init__(self, template_name, vm_name):
        self.ovfFile = None
        self.ovf_xml_dom = None
        self.vm_name = vm_name
        self.template_name = template_name
        self.vh_ident_counter = 1
        self.ovf_template_settings = dict()
        self.ovf_template_settings["vm_id"] = "0"
        self.ovf_template_settings["template_name"] = string.join(template_name, "")
        self.ovf_template_settings["vm_name"] = string.join(vm_name, "")
        self.ovf_template_settings["domain_type"] = "openvz" 
        self.ovf_template_settings["memory"] = str(constants.OPENVZ_DEFAULT_MEMORY)
        self.ovf_template_settings["min_memory"] = str(constants.OPENVZ_DEFAULT_MEMORY)
       	self.ovf_template_settings["max_memory"] = str(constants.OPENVZ_DEFAULT_MEMORY)
        self.ovf_template_settings["vcpu"] = str(constants.OPENVZ_DEFAULT_VCPU)
        self.ovf_template_settings["min_vcpu"] = str(constants.OPENVZ_DEFAULT_VCPU)
        self.ovf_template_settings["max_vcpu"] = str(constants.OPENVZ_DEFAULT_VCPU)
        self.ovf_template_settings["disk"] = str(constants.OPENVZ_DEFAULT_DISK)
        self.ovf_template_settings["min_disk"] = str(constants.OPENVZ_DEFAULT_DISK)
        self.ovf_template_settings["max_disk"] = str(constants.OPENVZ_DEFAULT_DISK)
        self.ovf_template_settings["vcpulimit"] = str(constants.OPENVZ_DEFAULT_VCPULIMIT)  
        self.ovf_template_settings["min_vcpulimit"] = str(constants.OPENVZ_DEFAULT_VCPULIMIT) 
        self.ovf_template_settings["max_vcpulimit"] = str(constants.OPENVZ_DEFAULT_VCPULIMIT)
        self.ovf_template_settings["ip_address"] = "192.168.0.1"
        self.ovf_template_settings["nameserver"] = "192.168.0.1"
        self.ovf_template_settings["passwd"] = ""
        #ToDo: VETH support
        #self.ovf_template_settings["veth"] = "0"

        self.unarchiveOVF()
        self.__getOVFXML()
        self.openvz_configuration = None


    def cleanup(self):
        """
        Clean up system from (partial) template deployment.
        Steps for clean up:
            - delete deployed file based disk images
            - destroy OpenVZ CT if it is already been defined

        @return: True if cleanup was successful
        @rtype: Boolean
        """
        try:
            (status, output) = commands.getstatusoutput("vzctl stop %d" % (int(self.ovf_template_settings["vm_id"])))
            (status, output) = commands.getstatusoutput("vzctl destroy %d" % (int(self.ovf_template_settings["vm_id"])))
        except:
            pass
        return True


    def unarchiveOVF(self):
        """
        Unarchive OVF template tar archive to template deploy directory
            
        @return: True if unarchiving OVF template was successful
        @rtype: Boolean
        """
        template_archive_path = "%s%s.tar" % (constants.TEMPLATE_OPENVZ, self.template_name)
       	template_path =	"%s%s/" % (constants.DEPLOY_TEMPLATE_OPENVZ, self.template_name)
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

            try:
                open("%s%s" % (constants.ORIGINAL_TEMPLATE_OPENVZ, member), "r")
            except:
         	if (member.endswith(".tar.gz")):
                    commands.getoutput("ln -s %s%s %s%s" % (template_path, member, constants.ORIGINAL_TEMPLATE_OPENVZ, member))

            try:
       	       	(status, output) = commands.getstatusoutput("ls -l %s/%s | awk '{print $11}'" % (constants.ORIGINAL_TEMPLATE_OPENVZ, member));
                if (output != "%s%s" % (template_path, member)):
                    raise Exception
            except:
                if (member.endswith(".tar.gz")):
                    try:
                        os.remove("%s%s" % (constants.ORIGINAL_TEMPLATE_OPENVZ, member))
                    except:
                        pass
                    commands.getoutput("ln -s %s%s %s%s" % (template_path, member, constants.ORIGINAL_TEMPLATE_OPENVZ, member))
       	return True

                                    
    def defineOpenvzCT(self):
        """
        Define OpenVZ CT using Libvirt API and previously generated OpenVZ configuration

        @return: True if defining OpenVZ CT was successful   
        @rtype: Boolean
        """

        #Network configuration for VETH
        #ToDo: implement support for VETH

        #Network configuration for VENET
        (status, output) = commands.getstatusoutput("vzctl set %d --ipadd %s --save" % (int(self.ovf_template_settings["vm_id"]), self.ovf_template_settings["ip_address"]))
        if (status != 0):
            print output
            raise Exception, "Unable to define OpenVZ CT (IP address adding failed)"

	(status, output) = commands.getstatusoutput("vzctl set %d --nameserver %s --save" % (int(self.ovf_template_settings["vm_id"]), self.ovf_template_settings["nameserver"]))
       	if (status != 0):
            raise Exception, "Unable to define OpenVZ CT (Nameserver address adding failed)"

        (status, output) = commands.getstatusoutput("vzctl set %d --hostname %s --save" % (int(self.ovf_template_settings["vm_id"]), self.ovf_template_settings["vm_name"]))
        if (status != 0):
            raise Exception, "Unable to define OpenVZ CT (Hostname adding failed)"

        (status, output) = commands.getstatusoutput("vzctl set %d --userpasswd root:%s --save" % (int(self.ovf_template_settings["vm_id"]), self.ovf_template_settings["passwd"]))
        if (status != 0):
            raise Exception, "Unable to define OpenVZ CT (Setting root password failed)"

        (status, output) = commands.getstatusoutput("vzctl start %d" % (int(self.ovf_template_settings["vm_id"])))
        if (status != 0):
            raise Exception, "Unable to define OpenVZ CT (CT starting failed)"

        return True


    def __getOpenvzCTList(self):
        """
	Return a list of current OpenVZ CTs (both running and stopped)

        @return: List of OpenVZ CTs on current machine
        @rtype: List
        """
        (status, output) = commands.getstatusoutput("vzlist -H -o ctid,hostname")
        if (status != 0):
            return []
        output_list = output.split("\n")
        ct_list = []
        for item in output_list:
            ct_list.append(item.rstrip().lstrip().split()[1])
        return ct_list


    def __getOpenvzCTIdList(self):
        """
        Return a list of current OpenVZ CTs (both running and stopped)

        @return: List of OpenVZ CTs on current machine
        @rtype: List
        """
        conn = libvirt.open("openvz:///system")
        id_list = conn.listDefinedDomains();
        id_list2 = conn.listDomainsID()
        for id in id_list2:
            id = int(id)
        return id_list + id_list2


    def __getTemplateList(self):
        """
        Return a list of current templates

        @return: List of OVF templates/appliances on OpenNode server
        @rtype: List
        """
        template_list = os.listdir(constants.TEMPLATE_OPENVZ)
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
            self.ovfFile = OvfFile("%s%s/%s.ovf" % (constants.DEPLOY_TEMPLATE_OPENVZ, self.template_name, self.template_name))
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
        system_dom = vh_dom.getElementsByTagName("System")[0]  
        system_type_dom = system_dom.getElementsByTagName("vssd:VirtualSystemType")[0]
        system_type = system_type_dom.firstChild.nodeValue
        if (system_type != "openvz"):
            raise Exception, "Given template is not compatible with OpenVZ on OpenNode server"

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
                bound = "normal"
                if (item_dom.hasAttribute("ovf:bound")):
                    bound = item_dom.getAttribute("ovf:bound")
                if (bound == "min"):
                    self.ovf_template_settings["min_memory"] = str(int(vq_dom.firstChild.nodeValue))
                elif (bound == "max"):
                    self.ovf_template_settings["max_memory"] = str(int(vq_dom.firstChild.nodeValue))
                else:
                    self.ovf_template_settings["memory"] = str(int(vq_dom.firstChild.nodeValue))


        self.ovf_template_settings["vm_id"] = self.__getAvailableCTID()

        self.ovf_template_settings.update(openvzcfgproducer.calculateSystemMinMax(self.ovf_template_settings))

        return self.ovf_template_settings


    def __getAvailableCTID(self):
        """
        Get next available IF for new OpenVZ CT

        @return: Next available ID for new OpenVZ CT
        @rtype: Integer
        """
        ct_id_list = self.__getOpenvzCTIdList()

        max_ct_id = 0

        for ct_id in ct_id_list:
            if (int(ct_id) > int(max_ct_id)):
                max_ct_id = int(ct_id)

        if (max_ct_id < 100):
            max_ct_id = 100

        return max_ct_id + 1


    def checkMainSettings(self, ovf_template_settings):
        """
	Check OpenVZ CT main settings

        @param ovf_template_settings: User updated dictionary of OVF configuration settings
        @type ovf_template_settings: Dictionary

        @return: Dictionary containing error messages for values passed by the user
        @rtype: Dictionary
        """
	errors_dict = dict()

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

        try:
            if ("vcpulimit" in ovf_template_settings):
                vcpulimit = ovf_template_settings["vcpulimit"]
            else:
                vcpulimit = self.ovf_template_settings["vcpulimit"]
            min_vcpulimit = self.ovf_template_settings["min_vcpulimit"]
            max_vcpulimit = self.ovf_template_settings["max_vcpulimit"]
            if (int(vcpulimit) < int(min_vcpulimit) or int(vcpulimit) > int(max_vcpulimit)):
                errors_dict["vcpulimit"] = "Virtual CPU limit out of template limits"
            if (int(vcpulimit) < 0 or int(vcpulimit) > 100):
                errors_dict["vcpulimit"] = "Virtual CPU limit must be between 0 and 100"
        except:
            errors_dict["vcpulimit"] = "Virtual CPU limit must be integer"

        try:
            if ("disk" in ovf_template_settings):
                disk = ovf_template_settings["disk"]
            else:
                disk = self.ovf_template_settings["disk"]
            min_disk = self.ovf_template_settings["min_disk"]
            max_disk = self.ovf_template_settings["max_disk"]
            if (int(disk) < int(min_disk) or int(disk) > int(max_disk)):
                errors_dict["disk"] = "Disk size limit out of template limits"
        except:
            errors_dict["disk"] = "Disk size limit must be integer"

        if ("ip_address" in ovf_template_settings):
            if (not(self.__checkIpFormat(ovf_template_settings["ip_address"]))):
                errors_dict["ip_address"] = "IP address not in correct format"
            (status, output) = commands.getstatusoutput("ping %s -c 1" % (ovf_template_settings["ip_address"]))
            if (status == 0):
                errors_dict["ip_address"] = "IP address already present in network"

        if ("nameserver" in ovf_template_settings):
            if (not(self.__checkIpFormat(ovf_template_settings["nameserver"]))):
                errors_dict["nameserver"] = "Nameserver address not in correct format"
       	    (status, output) = commands.getstatusoutput("ping %s -c 1" % (ovf_template_settings["nameserver"]))
       	    if (status != 0):
                errors_dict["nameserver"] = "Nameserver address not present in network"

        if ("passwd" in ovf_template_settings):
            if (len(ovf_template_settings["passwd"]) < 6):
                errors_dict["passwd"] = "Password must be at least 6 characters long"


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
        
        if (len(errors_dict) > 0):
            return errors_dict
        else:
            if ("memory" in ovf_template_settings):
               	self.ovf_template_settings["memory"] = ovf_template_settings["memory"]
            if ("vcpu" in ovf_template_settings):
                self.ovf_template_settings["vcpu"] = ovf_template_settings["vcpu"]
            if ("ip_address" in ovf_template_settings):
                self.ovf_template_settings["ip_address"] = ovf_template_settings["ip_address"]
            if ("nameserver" in ovf_template_settings):
                self.ovf_template_settings["nameserver"] = ovf_template_settings["nameserver"]
            if ("disk" in ovf_template_settings):
                self.ovf_template_settings["disk"] = ovf_template_settings["disk"]
            if ("vcpulimit" in ovf_template_settings):
                self.ovf_template_settings["vcpulimit"] = ovf_template_settings["vcpulimit"]
            if ("passwd" in ovf_template_settings):
                self.ovf_template_settings["passwd"] = ovf_template_settings["passwd"]
            #ToDo: VETH support
            #if ("veth" in ovf_template_settings):
            #    try:
            #        veth = int(ovf_template_settings["veth"])
            #        if (veth == 0):
            #            self.ovf_template_settings["veth"] = "0"
            #        else:
            #            self.ovf_template_settings["veth"] = "1"
            #    except:
            #        self.ovf_template_settings["veth"] = "0"
            #else:
            #    self.ovf_template_settings["veth"] = "0"
            return dict()


    def testSystem(self):
        """
        Test system compatibility for OVF template/appliance deployment

        @return: True if system is compatible for OVF template/appliance deployment.
        @rtype: Boolean
        """
        if (self.vm_name in self.__getOpenvzCTList()):
            raise Exception, "OpenVZ CT already exists"
        if (self.ovf_template_settings["vm_id"] in self.__getOpenvzCTIdList()):
            raise Exception, "OpenVZ CT already exists"
        if (not(self.template_name in self.__getTemplateList())):
            raise Exception, "Template does not exist"
        return True


    def writeOpenVZConfiguration(self):
        """
        Write OpenVZ CT configuration prepared by the __generateOpenvzConfiguration() method to a file.

        @return: OpenVZ CT configuration 
        @rtype: String
        """
        file_ptr = open("%s%s.conf" % (constants.INSTALL_CONFIG_OPENVZ, self.ovf_template_settings["vm_id"]), "w")
        file_ptr.write(self.openvz_configuration)
        file_ptr.close()
        commands.getstatusoutput("chmod 644 %s%s.conf" % (constants.INSTALL_CONFIG_OPENVZ, self.ovf_template_settings["vm_id"]))
        return self.openvz_configuration


    def generateOpenvzConfiguration(self):
        """
        Prepare OpenVZ CT configuration file from OVF template/appliance.

        @return: OpenVZ CT configuration
        @rtype: String
        """
        self.openvz_configuration = ""
        vm_configuration = ""

        try:
            fp = open("/etc/vz/conf/%d.conf" % (int(self.ovf_template_settings["vm_id"])), "r")
            vm_configuration = fp.read()
            fp.close()
        except:
            pass

        non_ubc_conf = openvzcfgproducer.getOpenvzNonUbcConf(vm_configuration)
        

        generator_list = [str(self.ovf_template_settings["memory"]),
                          str(int(self.ovf_template_settings["disk"])/1024),
                          str(self.ovf_template_settings["vcpu"]),
                          str(self.ovf_template_settings["vcpulimit"])]

        conf_generator = vzcfgproducer.VzCfgProducer(generator_list)
        
        ubc_conf = conf_generator.get_vzcfg_base()

        self.openvz_configuration = "%s%s\n\n" % (ubc_conf, non_ubc_conf)

        return self.openvz_configuration


    def prepareFileSystem(self):
        """
        Create OpenVZ CT with its prepared filesystem            

        @return: True if ct file system preparation was successful
        @rtype: Boolean
        """
        (status, output) = commands.getstatusoutput("vzctl create %s --ostemplate %s" % (self.ovf_template_settings["vm_id"], self.template_name))
	(status, output) = commands.getstatusoutput("chmod 755 /vz/private/%s" % (self.ovf_template_settings["vm_id"]))
        return True


    def __checkIpFormat(self, ip):
        num=ip.split(".")

        if not len(num)==4:
            return False

        for n in num:
            try:
                if int(n) < 0 or int(n) > 255:
                    return False
            except:
                return False

        return True

