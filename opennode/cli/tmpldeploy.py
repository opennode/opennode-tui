"""OpenNode CLI Template Deploy Menu"""

from snack import SnackScreen, Button, GridForm, ButtonChoiceWindow, Textbox, Entry, Listbox

import os
import traceback
import logging


from constants import *

from opennode.cli.ovfopenvz import *
from opennode.cli.ovfkvm import *


class TemplateDeploy(object):
    """OpenNode Management Menu Template Creation Library"""

    def __init__(self):
        logging.basicConfig(filename=LOG_FILENAME,level=logging.ERROR)


    def __printInformation(self, text):
        """
        Print out information text
        """
        print str(text)


    def run(self, omsInstall=False):
        """Let user select a template and deploy it to a virtual machine"""
        deploy_converter = None
        try:
            if (not(omsInstall)):
                screen = SnackScreen()
                #Ask user for a action to perform
                result = ButtonChoiceWindow(screen, "OpenNode Management Utility", "Select type of template to be deployed", [("Deploy KVM template",0), ("Deploy OpenVZ template",1), ("Main menu",2)])
                #Close snack screen
                screen.finish()

       	    if (not(omsInstall)):
                hypervizor = ""
                if (result == 0):
                    hypervizor = "kvm"
                elif (result == 1):
                    hypervizor = "openvz"
                else:
                    return 0
            else:
                hypervizor = "openvz"

            (template_name, vm_name) = self.__displayDeployTemplate(hypervizor, omsInstall)

            if (template_name is None):
                return 0

            if (hypervizor == "openvz"):
                deploy_converter = OVF2Openvz(template_name, vm_name)
            else:
                deploy_converter = OVF2KVM(template_name, vm_name)
            
            deploy_converter.unarchiveOVF()
            template_settings = deploy_converter.parseOVFXML()

            try: 
                deploy_converter.testSystem()
            except Exception, err:
                self.__displayErrorScreen(str(err))
                return 0

            while (True):
                template_settings = self.__displayVMDetails(hypervizor, template_settings, omsInstall)
                if (template_settings is None):
                    return 0
                template_errors = deploy_converter.updateOVFSettings(template_settings)
                if (len(template_errors) > 0):
                    error_string = ""
                    for (k, v) in template_errors.items():
                        error_string = error_string + v + " "
                    self.__displayErrorScreen(error_string)
                    continue
                break

            if (hypervizor == "openvz"):
                self.__printInformation("Copying OpenVZ template file system (this may take a while)")
                deploy_converter.prepareFileSystem()

                self.__printInformation("Generating OpenVZ CT configuration")
                deploy_converter.generateOpenvzConfiguration()
                deploy_converter.writeOpenVZConfiguration()

                self.__printInformation("Finalyzing OpenVZ template deployment")
                deploy_converter.defineOpenvzCT()
                self.__displayInfoScreen("OpenVZ template deployed successfully")
            else:
                self.__printInformation("Copying KVM template disks (this may take a while)")
                deploy_converter.prepareFileSystem()

                self.__printInformation("Generating KVM VM configuration")
                deploy_converter.generateKVMLibvirtXML()

                self.__printInformation("Finalyzing KVM template deployment")
                deploy_converter.defineKVMVM()
                self.__displayInfoScreen("KVM template deployed successfully")
        except:
            raise
            self.__displayErrorScreen("Template creation failed.")
            try:
                deploy_converter.cleanup()
            except:
                pass
            logging.error(traceback.format_exc())
            return 1
        return 0


    def __displayErrorScreen(self, error_text="An error occurred."):
        """Display error message on error screen"""
        screen = SnackScreen()
        form = GridForm(screen, "Error occurred.", 1, 3)
        text1 = Textbox(60, 2, error_text, 0, 0)
        text2 = Textbox(60, 2, "Please try again.", 0, 0)
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


    def __displayDeployTemplate(self, hypervizor, omsInstall=False):
        """Display template deploy screen"""
        if (hypervizor == "openvz"):
            template_list = self.__getTemplateList(hypervizor)
            if (omsInstall):
                if ("opennode-oms" in template_list):
                    template_list = ["opennode-oms"]
                else:
       	       	    template_list = []

            if (len(template_list) == 0):
       	       	self.__displayErrorScreen("No OpenVZ templates found on OpenNode.")
                return (None, None)
            listbox1 = Listbox(7, 1, 0, 30, 1)
            for template in template_list:
                listbox1.append(template, template)
            text1 = Textbox(40, 2, "Select %s template to be deployed" % (hypervizor.upper()), 0, 0)
            text2 = Textbox(40, 2, "(Host)name of VM to be deployed", 0, 0)
            spacer1 = Textbox(1, 1, "", 0, 0)
       	    spacer2 = Textbox(1, 1, "",	0, 0)
            spacer3 = Textbox(1, 1, "", 0, 0)
            entry1 = Entry(30, "virtual_machine.example.com")
            button1 = Button("Deploy selected template")
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
                    check = True
                else:
                    self.__displayErrorScreen("No VM name given.")
                    continue
                screen.finish()
            return (listbox1.current(), entry1.value())
        else:
            template_list = self.__getTemplateList(hypervizor)
            if (len(template_list) == 0):
                self.__displayErrorScreen("No KVM templates found on OpenNode.")
                return (None, None)
            listbox1 = Listbox(7, 1, 0, 30, 1)
            for template in template_list:
                listbox1.append(template, template)
            text1 = Textbox(40, 2, "Select %s template to be deployed" % (hypervizor.upper()), 0, 0)
            text2 = Textbox(40, 2, "(Host)name of VM to be deployed?", 0, 0)
            spacer1 = Textbox(1, 1, "", 0, 0)
            spacer2 = Textbox(1, 1, "", 0, 0)
            spacer3 = Textbox(1, 1, "", 0, 0)
            entry1 = Entry(30, "virtual_machine.example.com")
            button1 = Button("Deploy selected template")
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
                    check = True
                else:
                    self.__displayErrorScreen("No VM name given.")
                    continue
                screen.finish()
            return (listbox1.current(), entry1.value())


    def __displayVMDetails(self, hypervizor, template_settings, omsInstall=False):
        """Display configuration details of new VM"""
        if (hypervizor == "openvz"):
            text1 = Textbox(20, 1, "Memory size (MB):", 0, 0)
            text2 = Textbox(20, 1, "Memory min/max:", 0, 0)
            text3 = Textbox(20, 1, "Number of CPUs:", 0, 0)
            text4 = Textbox(20, 1, "CPU number min/max:", 0, 0)
            text5 = Textbox(20, 1, "CPU usage limit (%):", 0, 0)
            text6 = Textbox(20, 1, "CPU usage min/max:", 0, 0)
            text7 = Textbox(20, 1, "Disk size (GB):", 0, 0)
            text8 = Textbox(20, 1, "Disk size min/max:", 0, 0)
            text9 = Textbox(20, 1, "IP-address:", 0, 0)
            text10 = Textbox(20, 2, "Nameserver:", 0, 0)

            #ToDo: VETH support
            #text13 = Textbox(20, 2, "Use VETH:", 0, 0)

            text11 = Textbox(20, 1, "Root password:", 0, 0)
            text12 = Textbox(20, 2, "Root password x2:", 0, 0)

            entry1 = Entry(20, str(template_settings["memory"]))
            minmax1 = Textbox(20, 1, "%s / %s" % (template_settings["min_memory"], template_settings["max_memory"]), 0, 0)
       	    entry2 = Entry(20, str(template_settings["vcpu"]))
            minmax2 = Textbox(20, 1, "%s / %s" % (template_settings["min_vcpu"], template_settings["max_vcpu"]), 0, 0)
            entry3 = Entry(20, str(template_settings["vcpulimit"]))
            minmax3 = Textbox(20, 1, "%s / %s" % (template_settings["min_vcpulimit"], template_settings["max_vcpulimit"]), 0, 0)
       	    entry4 = Entry(20, str(int(template_settings["disk"])/1024))
            minmax4 = Textbox(20, 1, "%s / %s" % (str(int(template_settings["min_disk"])/1024), str(int(template_settings["max_disk"])/1024)), 0, 0)
       	    entry5 = Entry(20, str(template_settings["ip_address"]))
       	    entry6 = Entry(20, str(template_settings["nameserver"]))
            
            #ToDo: VETH support
            #entry9 = Checkbox("", isOn = 0)

            entry7 = Entry(20, str(template_settings["passwd"]), password = 1)
            entry8 = Entry(20, str(template_settings["passwd"]), password = 1)

            button1 = Button("Save VM settings")
            button2 = Button("Main menu")

            check = False
            while (not(check)):
                screen = SnackScreen()
                form = GridForm(screen, "OpenNode Management Utility", 2, 14)
                form.add(text1, 0, 0)
       	       	form.add(entry1, 1, 0)
                form.add(text2, 0, 1)
                form.add(minmax1, 1, 1)
                form.add(text3, 0, 2)
       	       	form.add(entry2, 1, 2)
                form.add(text4, 0, 3)
                form.add(minmax2, 1, 3)
                form.add(text5, 0, 4)
       	       	form.add(entry3, 1, 4)
                form.add(text6, 0, 5)
                form.add(minmax3, 1, 5)
                form.add(text7, 0, 6)
       	       	form.add(entry4, 1, 6)
                form.add(text8, 0, 7)
                form.add(minmax4, 1, 7)
                form.add(text9, 0, 8)
       	       	form.add(entry5, 1, 8)
                form.add(text10, 0, 9)
       	       	form.add(entry6, 1, 9)
                #form.add(text13, 0, 10)
                #form.add(entry9, 1, 10)
                form.add(text11, 0, 11)
                form.add(entry7, 1, 11)
                form.add(text12, 0, 12)
                form.add(entry8, 1, 12)

                form.add(button1, 0, 13)
                form.add(button2, 1, 13)
                form_result = form.run()
                screen.finish()
                if (form_result == button2):
                    return None
                #Memory input checking
                try:
                    int(entry1.value())
                except:
                    self.__displayErrorScreen("Memory size must be in integers.")
                    continue
                if (int(entry1.value()) < int(template_settings["min_memory"]) or int(entry1.value()) > int(template_settings["max_memory"])):
                    self.__displayErrorScreen("Memory size out of template limits.")
                    continue

                template_settings["memory"] = str(entry1.value())

                #CPU no. input checking
                try:
                    int(entry2.value())
                except:
                    self.__displayErrorScreen("CPU count must be in integers.")
                    continue
                if (int(entry2.value()) < int(template_settings["min_vcpu"]) or int(entry2.value()) > int(template_settings["max_vcpu"])):
                    self.__displayErrorScreen("CPU count out of template limits.")
                    continue

       	       	template_settings["vcpu"] = entry2.value()

                #CPU usage limit input checking
                try:
                    int(entry3.value())
                except:
                    self.__displayErrorScreen("CPU usage limit must be in integers.")
                    continue
                if (int(entry3.value()) < int(template_settings["min_vcpulimit"]) or int(entry3.value()) > int(template_settings["max_vcpulimit"])):
                    self.__displayErrorScreen("CPU usage limit out of template limits.")
                    continue
                if (int(entry3.value()) < 0 or int(entry3.value()) > 100):
                    self.__displayErrorScreen("CPU usage limit must be between 0 and 100.")
                    continue

       	       	template_settings["vcpulimit"] = entry3.value()

                #Disk input checking
                try:
                    int(entry4.value())
                except:
                    self.__displayErrorScreen("Disk size must be in integers.")
                    continue
                if (int(entry4.value()) < int(template_settings["min_disk"])/1024 or int(entry4.value()) > int(template_settings["max_disk"])/1024):
                    self.__displayErrorScreen("Disk size out of template limits.")
                    continue

       	       	template_settings["disk"] = str(int(entry4.value())*1024)

                #IP-address input check
                if (not(self.__checkIpFormat(entry5.value()))):
                    self.__displayErrorScreen("IP-address format not correct.")
                    continue

                template_settings["ip_address"] = entry5.value()

                #Nameserver input check
       	        if (not(self.__checkIpFormat(entry6.value()))):
                    self.__displayErrorScreen("Nameserver format not correct.")
                    continue

                template_settings["nameserver"] = entry6.value()

                #Password input check
                if (len(entry7.value()) < 6 or entry7.value() != entry8.value()):
                    self.__displayErrorScreen("Password must be at least 6 letters.")
                    continue
                    
                template_settings["passwd"] = entry7.value()

                #ToDo: VETH support
                #if (entry9.selected()):
                #    template_settings["veth"] = "1"
                #else:
                #    template_settings["veth"] = "0"

                break
            return template_settings
        else:
            text1 = Textbox(19, 1, "Memory size (MB):", 0, 0)
            text1_1 = Textbox(19, 1, "Memory min/max:", 0, 0)
            text2 = Textbox(19, 1, "Number of CPUs:", 0, 0)
            text2_1 = Textbox(19, 2, "CPU number min/max:", 0, 0)

            entry1 = Entry(20, str(template_settings["memory"]))
            minmax1 = Textbox(20, 1, "%s / %s" % (template_settings["min_memory"], template_settings["max_memory"]), 0, 0)
            entry2 = Entry(20, str(template_settings["vcpu"]))
            minmax2 = Textbox(20, 1, "%s / %s" % (template_settings["min_vcpu"], template_settings["max_vcpu"]), 0, 0)

            button1 = Button("Save VM settings")
            button2 = Button("Main menu")

            check = False
            while (not(check)):
                screen = SnackScreen()
                form = GridForm(screen, "OpenNode Management Utility", 2, 5)
                form.add(text1, 0, 0)
                form.add(entry1, 1, 0)
                form.add(text1_1, 0, 1)
                form.add(minmax1, 1, 1)
                form.add(text2, 0, 2)
                form.add(entry2, 1, 2)
                form.add(text2_1, 0, 3)
                form.add(minmax2, 1, 3)
                form.add(Button("Save VM settings"), 0, 4)
                form_result = form.run()
                screen.finish()
                if (form_result == button2):
                    return None
                #Memory input checking
                try:
                    int(entry1.value())
                except:
                    self.__displayErrorScreen("Memory size must be in integers.")
                    continue
                if (int(entry1.value()) < int(template_settings["min_memory"]) or int(entry1.value()) > int(template_settings["max_memory"])):
                    self.__displayErrorScreen("Memory size out of template limits.")
                    continue

                template_settings["memory"] = str(entry1.value())

                #CPU no. input checking
                try:
                    int(entry2.value())
                except:
                    self.__displayErrorScreen("CPU count must be in integers.")
                    continue
                if (int(entry2.value()) < int(template_settings["min_vcpu"]) or int(entry2.value()) > int(template_settings["max_vcpu"])):
                    self.__displayErrorScreen("CPU count out of template limits.")
                    continue
            
                template_settings["vcpu"] = entry2.value()

                break

            return template_settings


    def __getTemplateList(self, hypervizor):
        """Return a list of templates"""
        if (hypervizor == "openvz"):
            template_list = os.listdir(TEMPLATE_OPENVZ)
            template_list_out = []
            for template in template_list:
                if template.endswith(".tar"):
                    template_list_out.append(template.rsplit(".tar", 1)[0])
            return sorted(template_list_out)
        else:
            template_list = os.listdir(TEMPLATE_KVM)
            template_list_out = []
            for template in template_list:
                if template.endswith(".tar"):
                    template_list_out.append(template.rsplit(".tar", 1)[0])
            return sorted(template_list_out)


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

