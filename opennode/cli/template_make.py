#!/usr/bin/python

"""Provide OpenNode Management Menu Template Creation Library

Copyright 2010, Active Systems
Danel Ahman <danel@active.ee>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""

from snack import SnackScreen, Grid, Button, GridForm, ButtonChoiceWindow, Textbox, Entry, Button, Listbox

import os
import time
import urllib
import random
import commands
import sys
import xml.dom.minidom
import traceback
import logging
import tarfile
import shutil
from datetime import datetime

import libvirt

from opennode.cli.constants import *

from opennode.cli.kvmovf import *
from opennode.cli.openvzovf import *

class TemplateCreate(object):
    """OpenNode Management Menu Template Creation Library"""

    def __init__(self):
        logging.basicConfig(filename=LOG_FILENAME,level=logging.ERROR)


    def __printInformation(self, text):
        """
        Print out information text
        """
       	dt = datetime.now()
        text_prefix = "[OpenNode]"
        #print "[%02d.%02d.%04d %02d:%02d:%02d] %s %s" % (dt.day, dt.month, dt.year, dt.hour, dt.minute, dt.second, text_prefix, str(text))
        print str(text)


    def run(self):
        """Display template creation main screen"""
        create_converter = None
        try:
            screen = SnackScreen()
            result = ButtonChoiceWindow(screen, "OpenNode Management Utility", "Select type of template to be created", [("Create KVM template", 0), ("Create OpenVZ template", 1), ("Main menu", 2)])
            screen.finish()
            if (result == 0):
                hypervizor = "kvm"
            elif (result == 1):
                hypervizor = "openvz"
            else:
                return 0

            (vm_name, template_name) = self.__displayCreateTemplate(hypervizor)

            if (vm_name is None):
                return 0

            if (hypervizor == "openvz"):
                create_converter = Openvz2OVF(vm_name, template_name)
            else:
                create_converter = KVM2OVF(vm_name, template_name)

            try:
                create_converter.testSystem()
            except Exception, err:
                self.__displayErrorScreen(str(err))
                return 0

            template_settings = dict()

            if (hypervizor == "openvz"):
                self.__printInformation("Copying OpenVZ template file system (this may take a while)")
                create_converter.prepareFileSystem()
                template_settings = create_converter.parseOpenvzConfiguration()
            else:
                self.__printInformation("Copying KVM template file system (this may take a while)")
                create_converter.prepareFileSystem()
                template_settings = create_converter.parseKVMXML()

            while (True):
                template_settings = self.__displayTemplateDetails(hypervizor, template_settings)
                if (hypervizor == "openvz"):
                    template_errors = create_converter.updateOpenvzSettings(template_settings)
                else:
                    template_errors = create_converter.updateKVMSettings(template_settings)
                if (len(template_errors) > 0):
                    self.__displayErrorScreen("Inserted settings are not correct.")
                    continue
                break

            if (hypervizor == "openvz"):
                self.__printInformation("Generating OpenVZ template configuration")
                create_converter.generateOpenvzOVFXML()

                self.__printInformation("Finalyzing OpenVZ template creation")
                create_converter.archiveOVFTemplate()
                self.__displayInfoScreen("OpenVZ template created successfully")
            else:
                self.__printInformation("Generating KVM template configuration")
               	create_converter.generateKVMOVFXML()

                self.__printInformation("Finalyzing KVM template creation")
       	       	create_converter.archiveOVFTemplate()
                self.__displayInfoScreen("KVM template created successfully")
        except:
            self.__displayErrorScreen("Template creation failed.")
            try:
                create_converter.cleanup()
            except:
                pass
            logging.error(traceback.format_exc())
        return 0


    def __displayTemplateDetails(self, hypervizor, template_settings):
        """Display configuration details of new template"""
        if (hypervizor == "openvz"):
            text1 = Textbox(23, 1, "Memory size (MB):", 0, 0)
            text2 = Textbox(23, 1, "Memory size (min) (MB):", 0, 0)
            text3 = Textbox(23, 1, "Number of CPUs:", 0, 0)
            text4 = Textbox(23, 2, "Number of CPUs (min):", 0, 0)
             
            label1 = Textbox(20, 1, str(template_settings["memory"]), 0, 0)
            entry2 = Entry(20, str(template_settings["min_memory"]))
            label3 = Textbox(20, 1, str(template_settings["vcpu"]), 0, 0)
            entry4 = Entry(20, str(template_settings["min_vcpu"]))

            check = False
            while (not(check)):
                screen = SnackScreen()
                form = GridForm(screen, "OpenNode Management Utility", 2, 5)
                form.add(text1, 0, 0)
                form.add(label1, 1, 0)
                form.add(text2, 0, 1)
                form.add(entry2, 1, 1)
                form.add(text3, 0, 2)
                form.add(label3, 1, 2)
                form.add(text4, 0, 3)
                form.add(entry4, 1, 3)
                form.add(Button("Save template settings"), 0, 4)
                form.run()
                screen.finish()

                #Min memory input checking
                try:
                    int(entry2.value())
                except:
                    self.__displayErrorScreen("Min memory size must be in integers.")
                    continue

                if (int(template_settings["memory"]) < int(entry2.value())):
                    self.__displayErrorScreen("Min memory size can not be greater than memory size.")
                    continue

                template_settings["min_memory"] = str(entry2.value())

                #Min CPU  input checking
                try:
                    int(entry4.value())
                except:
                    self.__displayErrorScreen("Min CPU count must be in integers.")
                    continue

                if (int(template_settings["vcpu"]) < int(entry4.value())):
                    self.__displayErrorScreen("Min CPU count can not be greater than CPU count.")
                    continue

                template_settings["min_vcpu"] = entry4.value()

                break
            return template_settings
        else:
            text1 = Textbox(23, 1, "Memory size (MB):", 0, 0)
            text2 = Textbox(23, 1, "Memory size (min) (MB):", 0, 0)
            text3 = Textbox(23, 1, "Number of CPUs:", 0, 0)
            text4 = Textbox(23, 2, "Number of CPUs (min):", 0, 0)
                    
            label1 = Textbox(20, 1, str(template_settings["memory"]), 0, 0)
            entry2 = Entry(20, str(template_settings["min_memory"]))
            label3 = Textbox(20, 1, str(template_settings["vcpu"]), 0, 0)
            entry4 = Entry(20, str(template_settings["min_vcpu"]))

            check = False
            while (not(check)):
                screen = SnackScreen()
                form = GridForm(screen, "OpenNode Management Utility", 2, 5)
                form.add(text1, 0, 0)
                form.add(label1, 1, 0)
                form.add(text2, 0, 1)   
                form.add(entry2, 1, 1)
                form.add(text3, 0, 2)
                form.add(label3, 1, 2)
                form.add(text4, 0, 3)
                form.add(entry4, 1, 3)
                form.add(Button("Save template settings"), 0, 4)
                form.run()
                screen.finish()

                #Min memory input checking
                try:
                    int(entry2.value())
                except:
                    self.__displayErrorScreen("Min memory size must be in integers.")
                    continue

                if (int(template_settings["memory"]) < int(entry2.value())):
                    self.__displayErrorScreen("Min memory size can not be greater than memory size.")
                    continue

                template_settings["min_memory"] = str(entry2.value())

                #Min CPU  input checking
                try:
                    int(entry4.value())
                except:
                    self.__displayErrorScreen("Min CPU count must be in integers.")
                    continue

                if (int(template_settings["vcpu"]) < int(entry4.value())):
                    self.__displayErrorScreen("Min CPU count can not be greater than CPU count.")
                    continue

                template_settings["min_vcpu"] = entry4.value()

                break

            return template_settings


    def __displayCreateTemplate(self, hypervizor):
        """Display template create screen"""
        if (hypervizor == "openvz"):
            vm_dict = self.__getVMDict(hypervizor)
            template_list = self.__getTemplateList(hypervizor)
            if (len(vm_dict) == 0):
                self.__displayErrorScreen("No OpenVZ CTs found on OpenNode.")
                return (None, None)
            listbox1 = Listbox(7, 1, 0, 30, 1)
            for vm in vm_dict.keys():
                listbox1.append(vm, vm)
            text1 = Textbox(40, 2, "Select OpenVZ CT to be used for template", 0, 0)
            text2 = Textbox(40, 2, "Name of the template to be created", 0, 0)
            spacer1 = Textbox(1, 1, "", 0, 0)
            spacer2 = Textbox(1, 1, "", 0, 0)
            spacer3 = Textbox(1, 1, "", 0, 0)
            entry1 = Entry(30, "template_name")
            button1 = Button("Create new template")
       	    button2 = Button("Main menu")
            check = False
            while (not(check)):
                screen = SnackScreen()
                form = GridForm(screen, "OpenNode Management Utility", 1, 9)
                form.add(text1, 0, 0)
                form.add(listbox1, 0, 1)
                form.add(spacer1, 0, 2)
                form.add(text2, 0, 3)
                form.add(entry1, 0, 4)
                form.add(spacer2, 0, 5)
                form.add(button1, 0, 6)
                form.add(spacer3, 0, 7)
                form.add(button2, 0, 8)
                form_result = form.run()
                if (form_result == button2):
                    return (None, None)
                if (len(entry1.value()) > 0):
                    if (entry1.value() in template_list):
                        self.__displayErrorScreen("Template already exists.")
                        continue
                    check = True
                else:
                    self.__displayErrorScreen("No template name given.")
                    continue
                screen.finish()
            return (vm_dict[listbox1.current()], entry1.value())
        else:
            vm_dict = self.__getVMDict(hypervizor)
            template_list = self.__getTemplateList(hypervizor)
            if (len(vm_dict) == 0):
                self.__displayErrorScreen("No KVM VMs found on OpenNode.")
                return (None, None)
            listbox1 = Listbox(7, 1, 0, 30, 1)
            for vm in vm_dict.keys():
                listbox1.append(vm, vm)
            text1 = Textbox(40, 2, "Select KVM VM to be used for template", 0, 0)
            text2 = Textbox(40, 2, "Name of the template to be created", 0, 0)
            spacer1 = Textbox(1, 1, "", 0, 0)
            spacer2 = Textbox(1, 1, "", 0, 0)
       	    spacer3 = Textbox(1, 1, "", 0, 0)
            entry1 = Entry(30, "template_name")
            button1 = Button("Create new template")
            button2 = Button("Main menu")
            check = False
            while (not(check)):
                screen = SnackScreen()
                form = GridForm(screen, "OpenNode Management Utility", 1, 9)
                form.add(text1, 0, 0)
                form.add(listbox1, 0, 1)
                form.add(spacer1, 0, 2)
                form.add(text2, 0, 3)
                form.add(entry1, 0, 4)
                form.add(spacer2, 0, 5)
                form.add(button1, 0, 6)
                form.add(spacer3, 0, 7)
                form.add(button2, 0, 8)
                form_result = form.run()
                if (form_result == button2):
                    return (None, None)
                if (len(entry1.value()) > 0):
                    if (entry1.value() in template_list):
                        self.__displayErrorScreen("Template already exists.")
                        continue
                    check = True
                else:
                    self.__displayErrorScreen("No template name given.")
                    continue
                screen.finish()
            return (vm_dict[listbox1.current()], entry1.value())


    def __getTemplateList(self, hypervizor):
        """Return a list of templates"""
        if (hypervizor == "openvz"):
            try:
                template_list = os.listdir(TEMPLATE_OPENVZ)
            except:
                commands.getstatusoutput("mkdir -p %s" % (TEMPLATE_OPENVZ))
            template_list_out = []
            for template in template_list:
                if template.endswith(".tar"):
                    template_list_out.append(template.rsplit(".tar", 1)[0])
            return sorted(template_list_out)
        else:
            try:
                template_list = os.listdir(TEMPLATE_KVM)
            except:
                commands.getstatusoutput("mkdir -p %s" % (TEMPLATE_KVM))
            template_list_out = []
            for template in template_list:
                if template.endswith(".tar"):
                    template_list_out.append(template.rsplit(".tar", 1)[0])
            return sorted(template_list_out)


    def __getVMDict(self, hypervizor):
        """Return list of stopped virtual machines for given hypervizor"""
        if (hypervizor == 'openvz'):
            (status, output) = commands.getstatusoutput("vzlist -H -S -o ctid,hostname")
            if (status != 0 or len(output.strip().rstrip()) == 0):
                self.__displayErrorScreen("Could not retrieve OpenVZ CT list.")
                raise Exception, "Could not retrieve OpenVZ CT list"
            output_list = output.split("\n")
            vm_dict = dict()
            for item in output_list:
                ct_list = item.rstrip().lstrip().split()
                vm_dict[ct_list[1]] = ct_list[0]
            return vm_dict
        else:
            conn = libvirt.open("qemu:///system")
            name_list = conn.listDefinedDomains();
            vm_dict = dict()
            for name in name_list:
                vm_dict[name] = name
            return vm_dict
            

    def __displayErrorScreen(self, error_text="An error occurred."):
        """Display error message on error screen"""
        screen = SnackScreen()
        form = GridForm(screen, "OpenNode Management Utility.", 1, 3)
        text1 = Textbox(35, 2, error_text, 0, 0)
        text2 = Textbox(35, 2, "Please try again.", 0, 0)
        form.add(text1, 0, 0)
        form.add(text2, 0, 1)
        form.add(Button("OK"), 0, 2)
        form.runOnce()
        screen.finish()


    def __displayInfoScreen(self, info_text="Information."):
        """Display information message on information screen"""
        screen = SnackScreen()
        form = GridForm(screen, "Information.", 1, 2)
        text1 = Textbox(35, 2, info_text, 0, 0)
        form.add(text1, 0, 0)
        form.add(Button("OK"), 0, 1)
        form.runOnce()
        screen.finish()


