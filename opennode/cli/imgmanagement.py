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

"""Provide OpenNode ISO Images Management Library

Copyright 2010, Active Systems
Danel Ahman <danel@active.ee>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""

import os
import time
import urllib
import urllib2
import random
import commands
import sys
import traceback
import logging
import tarfile
from datetime import datetime

from xml.dom import minidom

from opennode.cli.constants import *


class IMGManagement(object):
    """OpenNode File Based Disk Images Management Library"""

    def __init__(self):
        logging.basicConfig(filename=LOG_FILENAME,level=logging.ERROR)


    def getFileBasedIMGList(self):
        """Get IMG images list from local server"""	
        img_list = []
        try:
       	    local_img_list = os.listdir("%s" % (FILE_BASED_IMAGE_DIR))
            for file in local_img_list:
                file = file.lstrip().rstrip()
                img_list.append(file)
        except:
            img_list = []
        return img_list


    def createFileBasedIMG(self, disk_name, disk_size):
        """Create a new KVM VM on file based image

        disk_name - disk image name
        disk_size - disk image size in megabytes
        """
        disk_name = str(disk_name)
        disk_size = str(disk_size)

        if (len(disk_name) == 0):
            raise "Disk name must not be empty"

        if (not(disk_size.isdigit())):
            raise "Disk image size is not integer"

        try:
            file = open("%s%s" % (FILE_BASED_IMAGE_DIR, disk_name),"r")
            file.close()
            check = True
        except:
            check = False

        if (check):
            raise "Disk image allready present"

        param_str = "create -f qcow2 %s%s %sM" % (FILE_BASED_IMAGE_DIR, disk_name, disk_size)
        (return_code,return_output) = commands.getstatusoutput("%s %s" % (KVM_QEMU_IMG, param_str))
        if (return_code != 0):
            raise "Creation of KVM disk based image failed. Traceback:\n%s" % (return_output)

        return 0


    def listFileBasedIMG(self):
        """List file based disk images"""
        (return_code,return_output) = commands.getstatusoutput("ls %s" % (FILE_BASED_IMAGE_DIR))
        if (return_code != 0):
            raise "Listing file based disk images failed"

        return return_output.split("\n")


    def removeFileBasedIMG(self, xml_data):
        """Remove KVM VM file based disk images"""
        #Parse XML to DOM object
        xml_doc = minidom.parseString(xml_data)
        #Find all disk tags in VM config
        disks = xml_doc.getElementsByTagName("disk")
        #Iterate through all of the disks
        for disk in disks:
            #Check if the disk is a type 'file'
            if (disk.hasAttribute("type") and disk.getAttribute("type") == "file"):
                #Check if the disk is a device 'disk'
                if (disk.hasAttribute("device") and disk.getAttribute("device") == "disk"):
                    sources = disk.getElementsByTagName("source")
                    #Iterate through all of the disk's sources
                    for source in sources:
                        if (source.hasAttribute("file")):
                            disk_path = source.getAttribute("file")
                            try:
                                os.remove(disk_path)
                            except:
                                pass
        return 0
