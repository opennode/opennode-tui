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

from opennode.cli.constants import *


class ISOManagement(object):
    """OpenNode ISO Images Management Library"""

    def __init__(self):
        logging.basicConfig(filename=LOG_FILENAME,level=logging.ERROR)


    def getISOList(self):
        """Get ISO images list"""
        return self.__getLocalISOList()


    def __getLocalISOList(self):
        """Get ISO images list from local server"""	
        iso_list = []
        try:
       	    local_iso_list = os.listdir("%s" % (ISO_IMAGE_DIR))
            for file in local_iso_list:
                file = file.lstrip().rstrip()
                iso_list.append(file)
        except:
            iso_list = []
        return iso_list
