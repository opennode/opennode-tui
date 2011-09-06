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

"""Provide OpenVZ configuration management features

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

import opennode.cli.constants as constants

refmem = "256"
refkmemsize = "14372700"


def parseOpenvzSettings(ovz_configuration):
    """
    Parse OpenVZ CT configuration to dictionary.

    @return: OpenVZ CT settings in a dictionary
    @rtype: Dictionary 
    """
    vm_settings = dict()
    vm_settings["vcpu"] = str(constants.OPENVZ_DEFAULT_VCPU)
    vm_settings["min_vcpu"] = str(constants.OPENVZ_DEFAULT_VCPU)
    vm_settings["max_vcpu"] = str(constants.OPENVZ_DEFAULT_VCPU)
    vm_settings["vcpulimit"] = str(constants.OPENVZ_DEFAULT_VCPULIMIT)
    vm_settings["min_vcpulimit"] = str(constants.OPENVZ_DEFAULT_VCPULIMIT)
    vm_settings["max_vcpulimit"] = str(constants.OPENVZ_DEFAULT_VCPULIMIT)
    vm_settings["memory"] = str(constants.OPENVZ_DEFAULT_MEMORY)
    vm_settings["min_memory"] = str(constants.OPENVZ_DEFAULT_MEMORY)
    vm_settings["max_memory"] = str(constants.OPENVZ_DEFAULT_MEMORY)
    vm_settings["disk"] = str(constants.OPENVZ_DEFAULT_DISK)
    vm_settings["max_disk"] = str(constants.OPENVZ_DEFAULT_DISK)
    vm_settings["min_disk"] = str(constants.OPENVZ_DEFAULT_DISK)
    vm_settings["ip_address"] = ""
    vm_settings["nameserver"] = ""
    vm_settings["hostname"] = ""
    vm_settings["onboot"] = "no"
    vm_settings["searchdomain"] = ""
    #ToDo: VETH support
    #vm_settings["veth"] = "0"

    lines = ovz_configuration.split("\n")
    for line in lines:
        line = line.lstrip().rstrip()
        if (len(line) > 0 and not(line.startswith("#"))):
            line_items = line.split("=", 1)
            if (len(line_items) == 2):
                option = line_items[0].lstrip().rstrip()
                if (option == "DISKSPACE"):
                    value = line_items[1].lstrip().rstrip().split(":")[0].replace("\"", "")
                    vm_settings["disk"] = str(int(value)/1024)
                elif (option == "CPUS"):
                    value = line_items[1].lstrip().rstrip().replace("\"", "")
                    vm_settings["vcpu"] = value
                elif (option == "CPULIMIT"):
                    value = line_items[1].lstrip().rstrip().replace("\"", "")
                    vm_settings["vcpulimit"] = value
                elif (option == "IP_ADDRESS"):
                    value = line_items[1].lstrip().rstrip().replace("\"", "")
                    vm_settings["ip_address"] = value
                elif (option == "NAMESERVER"):
       	       	    value = line_items[1].lstrip().rstrip().replace("\"", "")
       	       	    vm_settings["nameserver"] = value
                elif (option == "HOSTNAME"):
                    value = line_items[1].lstrip().rstrip().replace("\"", "")
                    vm_settings["hostname"] = value
                elif (option == "KMEMSIZE"):
                    value = int(line_items[1].lstrip().rstrip().split(":")[0].replace("\"", ""))
                    vm_settings["memory"] = str(value/int(refkmemsize)*int(refmem))
                elif (option == "ONBOOT"):
                    value = line_items[1].lstrip().rstrip().replace("\"", "")
                    vm_settings["onboot"] = value
                elif (option == "SEARCHDOMAIN"):
                    value = line_items[1].lstrip().rstrip().replace("\"", "")
                    vm_settings["searchdomain"] = value
                #ToDo: VETH support
                #elif (option == "NETIF"):
                #    if (len(value) > 3):
                #        vm_settings["veth"] = "1"

    return vm_settings


def getOpenvzNonUbcConf(ovz_configuration):
    """
    Get non-UBC part of the OpenVZ CT configuration. It is to be merged with newly calculated UBC part of the configuration.
                
    @return: OpenVZ CT non-UBC part of configuration
    @rtype: String
    """
    output_lines = []
    lines = ovz_configuration.split("\n")
    for line in lines:
        line_orig = line
        line = line.lstrip().rstrip()
        if (len(line) > 0 and not(line.startswith("#"))):
            line_items = line.split("=", 1)
            if (len(line_items) == 2):
                option = line_items[0].lstrip().rstrip()
                if (not(option in constants.OPENVZ_CONF_CREATOR_OPTIONS)):
                    output_lines.append(line_orig)
    return "\n".join(output_lines)


def calculateOpenvzNonUbcConf(ovf_template_settings):
    """
    Calculate non-UBC part of the OpenVZ CT configuration. It is to be merged with newly calculated UBC part of the configuration.

    @return: OpenVZ CT non-UBC part of configuration
    @rtype: String
    """
    out = ""
    out += "IP_ADDRESS=\"%s\"\n" % (str(ovf_template_settings["ip_address"]))
    out	+= "NAMESERVER=\"%s\"\n" % (str(ovf_template_settings["nameserver"]))
    out += "ONBOOT=\"%s\"\n" % (str(ovf_template_settings["onboot"]))
    out += "SEARCHDOMAIN=\"%s\"\n" % (str(ovf_template_settings["searchdomain"]))
    #if (ovf_template_settings["veth"] == 1):
    #    out += "NETIF=\"ifname=eth0,bridge=vmbr0\"\n"
    return out


def calculateSystemMinMax(ovf_template_settings):
    """
    Calculate OpenNode server's system minimum and maximum resource limits:

    Values to be calculated:
     - memory min/max size
     - CPU min/max count
     - CPU min/max usage limit
     - disk min/max size

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

    #CPU usage limit calculation
    ovf_template_settings["min_vcpulimit"] = "0"
    ovf_template_settings["max_vcpulimit"] = str(100*int(vcpu))

    #Disk space calculation
    disk_list = []
    (status, output) = commands.getstatusoutput("df /vz")
    if (status != 0):
        raise Exception, "Unable to calculate disk space"
    tmp_output = output.split("\n", 1)
    if (len(tmp_output) != 2):
        raise Exception, "Unable to calculate disk space"
    df_list = tmp_output[1].split()
    disk = str(int(df_list[3])/1024)
    ovf_template_settings["max_disk"] = disk
    if (int(ovf_template_settings["min_disk"]) > int(disk)):
        ovf_template_settings["min_disk"] = disk

    try:
        (status, output) = commands.getstatusoutput("vzquota show %s" % (ovf_template_settings["vm_id"]))
        if (status != 0):
            raise Exception, "Unable to calculate disk space"

        lines = output.split("\n")
        for line in lines:
            line_items = line.split()
            if (line_items[0] == "1k-blocks"):
                ovf_template_settings["min_disk"] = str(int(line_items[1])/1024)
                break
    except:
        pass

    return ovf_template_settings

