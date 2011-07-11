#!/usr/bin/python
###########################################################################
#
#    Copyright (C) 2009-2011 Active Systems LLC, 
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

"""Provide OpenNode Management Menu Constants Library

Copyright 2010, Active Systems
Danel Ahman <danel@active.ee>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""

KVM_VIRT_INSTALL = "virt-install "
KVM_QEMU_IMG = "qemu-img "

DRIVE_LETTERS = ["a","b","c","d","e","f","g","h","i","j","k","l","m","n","o","p","q","r","s","t","u","v","w","x","y","z"]

SYSTEM_ARCHES = ["x86_64", "i686"]
KVM_VIRT_TYPES = ["hvm"]
KVM_FEATURES = ["acpi", "apic", "pae"]

OS_VARIANTS = ["linux","rhel2.1","rhel3","rhel4","rhel5","centos5","fedora5","fedora6","fedora7","sles10","debianEtch","debianLenny",
               "generic26","generic24","windows","winxp","win2k","win2k3","vista","unix","solaris9","solaris10","freebsd6","openbsd4",
               "other","msdos","netware4","netware5","netware6"]

OS_TYPES = ["linux","windows","unix","other"]

OPENVZ_DEFAULT_MEMORY = 256
OPENVZ_DEFAULT_DISK = 2048
OPENVZ_DEFAULT_VCPU = 1
OPENVZ_DEFAULT_VCPULIMIT = 50

KVM_DEFAULT_MEMORY = 256
KVM_DEFAULT_VCPU = 1

OPENVZ_CONF_CREATOR_OPTIONS = ["NUMPROC", "AVNUMPROC", "NUMTCPSOCK", "NUMOTHERSOCK", "VMGUARPAGES", "KMEMSIZE", "TCPSNDBUF", "TCPRCVBUF",
                               "OTHERSOCKBUF", "DGRAMRCVBUF", "OOMGUARPAGES", "PRIVVMPAGES", "LOCKEDPAGES", "SHMPAGES", "PHYSPAGES",
                               "DCACHESIZE", "NUMFILE", "NUMFLOCK", "NUMPTY", "NUMSIGINFO", "NUMIPTENT", "DISKSPACE", "DISKINODES", 
                               "QUOTATIME", "CPUUNITS", "CPULIMIT", "CPUS", "IP_ADDRESS", "NAMESERVER", "SEARCHDOMAIN", "ONBOOT"]

DIR_OFFSET = ''

MIRROR_LIST = 'http://opennode.activesys.org/mirrorlist.txt'

TEMPLATE_DIR_OPENVZ = 'templates/openvz/' 
TEMPLATE_DIR_KVM = 'templates/kvm/'

TEMPLATE_ROOT_DIR = DIR_OFFSET+'/storage/'

LOCAL_TEMPLATE_LIST_DIR = DIR_OFFSET+'/opt/opennode/var/'

MINION_CONF = DIR_OFFSET+'/etc/certmaster/minion.conf'

FILE_BASED_IMAGE_DIR = DIR_OFFSET+'/storage/images/'

ISO_IMAGE_DIR = DIR_OFFSET+'/storage/iso/'

INSTALL_TEMPLATE_OPENVZ = DIR_OFFSET+'/vz/private/'
INSTALL_CONFIG_OPENVZ = DIR_OFFSET+'/etc/vz/conf/'

DEPLOY_TEMPLATE_OPENVZ = DIR_OFFSET+TEMPLATE_ROOT_DIR+TEMPLATE_DIR_OPENVZ+'deploy/'
ORIGINAL_TEMPLATE_OPENVZ = DIR_OFFSET+'/vz/template/cache/'

DEPLOY_TEMPLATE_KVM = DIR_OFFSET+TEMPLATE_ROOT_DIR+TEMPLATE_DIR_KVM+'deploy/'

TEMPLATE_KVM = DIR_OFFSET+TEMPLATE_ROOT_DIR+TEMPLATE_DIR_KVM
TEMPLATE_OPENVZ = DIR_OFFSET+TEMPLATE_ROOT_DIR+TEMPLATE_DIR_OPENVZ

LOG_FILENAME = DIR_OFFSET+'/var/log/opennode.log'

