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

"""Provide KVM VM creation from an ISO image

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
import subprocess
import shlex

import libvirt

import opennode_lib.constants as constants
import opennode_lib.kvmcfgproducer as kvmcfgproducer

import tarfile

class ISO2KVM:
    """Create KVM VM from ISO image"""

    def __init__(self, vm_name):
        self.vm_name = str(vm_name)
        self.os_variant	= ""
       	self.os_type = ""
       	self.iso_file =	""
       	self.disk_size = 0
       	self.bdisk_path = ""
       	self.memory = 0
       	self.noapic = ""
       	self.noacpi = ""
        self.system_min_max = kvmcfgproducer.calculateSystemMinMax({"min_vcpu":"0", "max_vcpu":"0", "min_memory":"0", "max_memory":"0"})
        self.disk_abs_path = "%s%s-image1.img" % (constants.FILE_BASED_IMAGE_DIR, vm_name)
        self.iso_abs_path = ""


    def setCreateSettings(self, os_variant, os_type, iso_path, disk_size, bdisk_path, memory, noapic, noacpi):
        self.os_variant = str(os_variant)
        self.os_type = str(os_type)
        self.iso_path = str(iso_path)
        self.disk_size = int(disk_size)
        self.bdisk_path = str(bdisk_path)
        self.memory = int(memory)
        if (len(noapic) > 0):
            self.noapic = "--noapic"
        if (len(noacpi) > 0):
            self.noacpi = "--noacpi"
        self.iso_abs_path = "%s%s" % (constants.ISO_IMAGE_DIR, iso_path)


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


    def testSystem(self):
        """
        Test system compatibility for KVM VM creation

        @return: True if system is compatible for OVF template/appliance deployment.
        @rtype: Boolean
        """
        if (self.vm_name in self.__getKVMVMList()):
            raise Exception, "KVM VM already exists"
        return True


    def checkMainSettings(self):
        """
	Check KVM VM main settings

        @return: Dictionary containing error messages for values passed by the user
        @rtype: Dictionary
        """
        errors_dict = dict()

        try:
            memory = self.memory
            min_memory = self.system_min_max["min_memory"]
            max_memory = self.system_min_max["max_memory"]
            if (int(memory) < int(min_memory) or int(memory) > int(max_memory)):
                errors_dict["memory"] = "Memory size out of limits"
        except:
            errors_dict["memory"] = "Memory size has to be integer"

        if (not(self.os_variant in constants.OS_VARIANTS)):
            errors_dict["os_variant"] = "Unknown OS variant"

        if (not(self.os_type in constants.OS_TYPES)):
            errors_dict["os_type"] = "Unknown OS type"

        try:
            fp = open(self.iso_abs_path, "r")
            fp.close()
        except:
            errors_dict["iso_path"] = "ISO image not found"

        try:
       	    fp = open(self.disk_abs_path, "r")
       	    fp.close()
            errors_dict["disk_path"] = "Disk already exists"
        except:
            pass

        if (len(self.bdisk_path) > 0):
            if (not(os.path.exists(self.bdisk_path))):
                errors_dict["bdisk_path"] = "Block device not found"


        return errors_dict


    def createVMFromISO(self):
        """Create KVM VM from ISO image"""
        disk = ""
        if (len(self.bdisk_path) > 0):
            disk = self.bdisk_path
        else:
            disk = "%s" % (self.disk_abs_path)
       	    (status, output) = commands.getstatusoutput("qemu-img create -f qcow2 %s %dG" % (disk, self.disk_size))
            if (status != 0):
                raise Exception, "Unable to create file based disk"

        cmdline = "virt-install --connect qemu:///system --name %s --ram %d --disk path=%s \
            --network=bridge:vmbr0 --vnc --os-type=%s --os-variant=%s --cdrom %s \
            --accelerate --noautoconsole %s %s" % (self.vm_name, self.memory, disk, self.os_type, self.os_variant, self.iso_abs_path, self.noapic, self.noacpi)
        args = shlex.split(cmdline)
        subprocess.Popen(args, cwd='/storage/images/')
        
        return 0
