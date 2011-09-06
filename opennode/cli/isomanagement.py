"""OpenNode ISO Images Management Library"""

import os
import logging

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
