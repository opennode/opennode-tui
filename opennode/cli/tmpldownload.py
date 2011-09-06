"""OpenNode Management Menu Template Download"""

from snack import SnackScreen, Button, GridForm, Textbox, CheckboxTree
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

from opennode.cli.constants import *
import opennode.cli.progress

class TemplateDownload(object):
    """OpenNode Management Menu Template Download Library"""

    def __init__(self):
        logging.basicConfig(filename=LOG_FILENAME,level=logging.ERROR)
        self.progressBarCounter = 0
        self.progressStartTime = None


    def __printInformation(self, text):
        """
        Print out information text
        """
        print str(text)


    def __prepareProgressBarHook(self):
        """Prepare variables needed to display progress bar"""
        self.progressBarCounter = 0
        self.progressStartTime = time.time()


    def __progressBarHook(self, downloaded, chunk, total):
        """Display download progress bar"""
        if (self.progressBarCounter % 10 == 0):
            progressTime = time.time()
            delta = progressTime - self.progressStartTime
            percentage = 100.0 * chunk * downloaded / total
            remaining = -1
            if (percentage > 0):
       	        total = 100 * delta / percentage
       	        remaining = int(total - delta)
            percentage = int(percentage)
            bar = opennode.cli.progress.printProgressBar(percentage, size = 50, remainingTime = remaining)
            print bar,
            sys.stdout.flush()
            print "\r",
        self.progressBarCounter += 1


    def __resetProgressBarHook(self):
        """Reset variables needed to show progress bar"""
        progressTime = time.time()
        delta = progressTime - self.progressStartTime
        remaining = int(delta)
        bar = opennode.cli.progress.printProgressBar(100, size = 50, remainingTime = remaining)
        print bar,
        sys.stdout.flush()
        print "\r"


    def deleteTemplate(self, hypervizor, template):
        """Delete template archive, file system files and its configuration file"""
        return self.__deleteLocalTemplate(hypervizor, template)


    def __deleteLocalTemplate(self, hypervizor, local_template):
        """Delete local template archive, file system files and its configuration file"""
        if (hypervizor == "openvz"):
            #Delete OpenVZ template and its files
            self.__printInformation("Deleting OpenVZ local template: %s" % (local_template))
            try:
                template_files = os.listdir("%s%s/" % (DEPLOY_TEMPLATE_OPENVZ, local_template))
                for template_file in template_files:
                    os.remove("%s%s/%s" % (DEPLOY_TEMPLATE_OPENVZ, local_template, template_file))
                os.rmdir("%s%s/" % (DEPLOY_TEMPLATE_OPENVZ, local_template))
            except:
                pass
            try:
                os.remove("%s%s.tar" % (TEMPLATE_OPENVZ, local_template))
            except:
                pass
            try:
       	        os.remove("%s%s.tar.md5" % (TEMPLATE_OPENVZ, local_template))
            except: 
                pass
            try:
                os.remove("%s%s.tar.gz" % (ORIGINAL_TEMPLATE_OPENVZ, local_template))
            except:
                pass
        elif (hypervizor == "kvm"):
            #Delete KVM template and its files
            self.__printInformation("Deleting KVM local template: %s" % (local_template))
            try:
       	        template_files = os.listdir("%s%s/" % (DEPLOY_TEMPLATE_KVM, local_template))
       	        for template_file in template_files:
   	       	    os.remove("%s%s/%s" % (DEPLOY_TEMPLATE_KVM, local_template, template_file))
       	        os.rmdir("%s%s/" % (DEPLOY_TEMPLATE_KVM, local_template))
            except:
                pass
            try:
                os.remove("%s%s.tar" % (TEMPLATE_KVM, local_template))
            except:
                pass
            try:
       	        os.remove("%s%s.tar.md5" % (TEMPLATE_KVM, local_template))
            except:
                pass
            try:
                os.remove("%s%s.tar.pfff" % (TEMPLATE_KVM, local_template))
            except:
                pass
        return True


    def __compareLocalRemoteTemplateList(self, hypervizor, local_template_list, selected_template_list, remote_template_list):
        """Compare local and remote template lists"""
        download_template_list = []
        for local_template in local_template_list:
            #Delete not selected templates
            if (not(local_template in selected_template_list)):
                self.__deleteLocalTemplate(hypervizor, local_template)
        for selected_template in selected_template_list:
            #Only download templates that are on server (selected list is merged from local and remote)
            if (selected_template in remote_template_list):
                download_template_list.append(selected_template)
        return download_template_list


    def getTemplateList(self, hypervizor):
        """Get template list"""
        return self.__getLocalTemplateList(hypervizor)


    def __getLocalTemplateList(self, hypervizor):
        """Get template list from local server"""	
        template_list = []
        try:
            if (hypervizor == "openvz"):
                local_template_list = os.listdir("%s" % (TEMPLATE_OPENVZ))
            else:
       	        local_template_list = os.listdir("%s" % (TEMPLATE_KVM))
            for file in local_template_list:
                file = file.lstrip().rstrip()
                if (file.endswith(".tar")):
                    template_list.append(file.split(".tar")[0])
        except:
            template_list = []
        return template_list


    def __getRemoteTemplateList(self, mirror, hypervizor):
        """Get template list from remote server"""
        if (hypervizor == "openvz"):
            template_dir = TEMPLATE_DIR_OPENVZ
        else:
            template_dir = TEMPLATE_DIR_KVM
        template_web = urllib2.urlopen("%s%stemplatelist.txt" % (mirror, template_dir))
        template_list_str = template_web.read()
        template_web.close()
        template_list_tmp = template_list_str.rstrip().lstrip().rsplit("\n")
        template_list = []
        for template in template_list_tmp:
            if (len(template) > 0):
                template_list.append(template)
        return template_list


    def __downloadRemoteTemplate(self, mirror, hypervizor, remote_template):
        """Download and unpack remote template"""
        if (hypervizor == "openvz"):
            #Download OpenVZ template
            path = "%s" % (TEMPLATE_OPENVZ)
            remote_path = "%s%s" % (mirror, TEMPLATE_DIR_OPENVZ)
            try:
                os.makedirs("%s" % (TEMPLATE_OPENVZ))
                os.makedirs("%s%s/" % (DEPLOY_TEMPLATE_OPENVZ, remote_template))
            except:
                pass
            check = True
            count = 0
            self.__printInformation("Checking OpenVZ template for update: %s" % (remote_template))
            while (check):
                urllib.urlretrieve("%s%s.tar.pfff" % (remote_path, remote_template), "%s%s.tar.pfff" % (path, remote_template))
                (return_code, return_output) = commands.getstatusoutput('cd %s && TEST=`pfff -k 6996807 -B %s.tar` && CORRECT=`cat %s.tar.pfff` && [ "$TEST" = "$CORRECT" ]' % (path, remote_template, remote_template))
                if (return_code == 0):
                    check = False
                    break
                else:
                    self.__printInformation("Downloading OpenVZ template: %s%s.tar" % (remote_path, remote_template))
                self.__prepareProgressBarHook()
                urllib.urlretrieve("%s%s.tar" % (remote_path, remote_template), "%s%s.tar" % (path, remote_template), self.__progressBarHook)
                self.__resetProgressBarHook()
                (return_code, return_output) = commands.getstatusoutput('cd %s && TEST=`pfff -k 6996807 -B %s.tar` && CORRECT=`cat %s.tar.pfff` && [ "$TEST" = "$CORRECT" ]' % (path, remote_template, remote_template))
                if (return_code == 0):
                    check = False
                    break
                else:
                    self.__printInformation("Re-Downloading OpenVZ template: %s%s.tar" % (remote_path, remote_template))
                    count = count + 1
                    try:
                        os.remove("%s%s.tar" % (path, remote_template))
                    except:
                        pass
                    try:
                        os.remove("%s%s.tar.md5" % (path, remote_template))
                    except:
                        pass
                    try:
                        os.remove("%s%s.tar.pfff" % (path, remote_template))
                    except:
                        pass
                if (count == 3):
                    self.__printInformation("Failed downloading OpenVZ template: %s%s.tar" % (remote_path, remote_template))
                    break
            if (not(check)):
                try:
                    template_files = os.listdir("%s%s/" % (DEPLOY_TEMPLATE_OPENVZ, remote_template))
                    for template_file in template_files:
                        os.remove("%s%s/%s" % (DEPLOY_TEMPLATE_OPENVZ, remote_template, template_file))
                    os.rmdir("%s%s/" % (DEPLOY_TEMPLATE_OPENVZ, remote_template))
                except:
                    pass
                tar_file = tarfile.open(name = "%s%s.tar" % (path, remote_template), mode = "r:")
                tar_file_members = tar_file.getnames()
                template_path = "%s%s/" % (DEPLOY_TEMPLATE_OPENVZ, remote_template)
                for member in tar_file_members:
                    tar_file.extract(member, template_path)
                    if (member.endswith(".tar.gz")):
                        commands.getoutput("ln -s %s%s %s%s" % (template_path, member, ORIGINAL_TEMPLATE_OPENVZ, member))
                tar_file.close()
        else:
            #Download KVM template
            path = "%s" % (TEMPLATE_KVM)
            remote_path = "%s%s" % (mirror, TEMPLATE_DIR_KVM)
            try:
                os.makedirs("%s" % (TEMPLATE_KVM))
                os.makedirs("%s%s/" % (DEPLOY_TEMPLATE_KVM, remote_template))
            except:
                pass
            check = True
            count = 0
            self.__printInformation("Checking KVM template for update: %s" % (remote_template))
            while (check):
                urllib.urlretrieve("%s%s.tar.pfff" % (remote_path, remote_template), "%s%s.tar.pfff" % (path, remote_template))
                (return_code, return_output) = commands.getstatusoutput('cd %s && TEST=`pfff -k 6996807 -B %s.tar` && CORRECT=`cat %s.tar.pfff` && [ "$TEST" = "$CORRECT" ]' % (path, remote_template, remote_template))
                if (return_code == 0):
                    check = False
                    break
                else:
                    self.__printInformation("Downloading KVM template: %s%s.tar" % (remote_path, remote_template))
                self.__prepareProgressBarHook()
                urllib.urlretrieve("%s%s.tar" % (remote_path, remote_template), "%s%s.tar" % (path, remote_template), self.__progressBarHook)
                self.__resetProgressBarHook()
                (return_code, return_output) = commands.getstatusoutput('cd %s && TEST=`pfff -k 6996807 -B %s.tar` && CORRECT=`cat %s.tar.pfff` && [ "$TEST" = "$CORRECT" ]' % (path, remote_template, remote_template))
                if (return_code == 0):
                    check = False
                    break
                else:
                    self.__printInformation("Re-Downloading KVM template: %s%s.tar" % (remote_path, remote_template))
                    count = count + 1
                    try:
                        os.remove("%s%s.tar" % (path, remote_template))
                    except:
                        pass
                    try:
                        os.remove("%s%s.tar.md5" % (path, remote_template))                              
                    except:
                        pass
                    try:
                        os.remove("%s%s.tar.pfff" % (path, remote_template))                              
                    except:
                        pass
                if (count == 3):
                    self.__printInformation("Failed downloading KVM template: %s%s.tar" % (remote_path, remote_template))
                    break
            if (not(check)):
                try:
                    template_files = os.listdir("%s%s/" % (DEPLOY_TEMPLATE_KVM, remote_template))
                    for template_file in template_files:
                        os.remove("%s%s/%s" % (DEPLOY_TEMPLATE_KVM, remote_template, template_file))
                    os.rmdir("%s%s/" % (DEPLOY_TEMPLATE_KVM, remote_template))
                except:
                    pass
                tar_file = tarfile.open(name = "%s%s.tar" % (path, remote_template), mode = "r:")
                tar_file_members = tar_file.getnames()
                template_path = "%s%s/" % (DEPLOY_TEMPLATE_KVM, remote_template)
                for member in tar_file_members:
                    tar_file.extract(member, template_path)
                tar_file.close()


    def __downloadRemoteTemplates(self, mirror, hypervizor, remote_template_list):
        """Download remote templates in template list"""
        for remote_template in remote_template_list:
            self.__downloadRemoteTemplate(hypervizor, mirror, remote_template)


    def __displayTemplates(self, hypervizor, remote_template_list, local_template_list):
        """Display list of templates to be downloaded"""
        if (len(remote_template_list + local_template_list) == 0):
            return []
        #Display checkbox list of templates 
        screen = SnackScreen()
        form = GridForm(screen, "OpenNode Management Utility", 1, 4)
        text = Textbox(50, 2, "Selected %s templates will not be deleted" % (hypervizor.upper()), 0, 0)
        checkbox_list = []
        checkbox_tree = CheckboxTree(10, 1, 50, 0, 0)
        for template in remote_template_list:
            if (template in local_template_list):
                checkbox_list.append(("(Remote) %s" % (template), 1))
            else:
                checkbox_list.append(("(Remote) %s" % (template), 0))
        for template in local_template_list:
            if (not(template in remote_template_list)):
                checkbox_list.append(("(Local ) %s" % (template), 1))
        checkbox_list = sorted(checkbox_list)
        for checkbox in checkbox_list:
            checkbox_tree.append(checkbox[0], None, checkbox[1])
        form.add(text, 0, 0)
        form.add(checkbox_tree, 0, 1)
        form.add(Button("Update selected"), 0, 2)
        form.runOnce()
        screen.finish()
        selected_template_list = checkbox_tree.getSelection()
        selected_template_list2 = []
        for selected in selected_template_list:
            if (len(selected) > 9):
                selected_template_list2.append(selected[9:])
        return selected_template_list2


    def runList(self):
        """List OpenVZ and KVM local and remote templates"""
        #Get template servers mirror list
        mirror = self.__getMirror()
        try:
            #Get OpenVZ local and remote template lists
            self.__printInformation("Fetching OPENVZ local template list")
            openvz_local_template_list = self.__getLocalTemplateList("openvz")
            self.__printInformation("Fetching OPENVZ remote template list")
            openvz_remote_template_list = self.__getRemoteTemplateList(mirror, "openvz")

            #Get KVM local and remote template lists
            self.__printInformation("Fetching KVM local template list")
            kvm_local_template_list = self.__getLocalTemplateList("kvm")
            self.__printInformation("Fetching KVM remote template list")
            kvm_remote_template_list = self.__getRemoteTemplateList(mirror, "kvm")

            self.__printInformation("Listing local OPENVZ templates")
            self.__printInformation("")
            for template in openvz_local_template_list:
                self.__printInformation("%s\t\t%s%s.tar" % (template, TEMPLATE_OPENVZ, template))
            self.__printInformation("")

            self.__printInformation("Listing local KVM templates")
            self.__printInformation("")
            for template in kvm_local_template_list:
                self.__printInformation("%s\t\t%s%s.tar" % (template, TEMPLATE_KVM, template))
            self.__printInformation("")

            self.__printInformation("Listing remote OPENVZ templates")
            self.__printInformation("")
            for template in openvz_remote_template_list:
                self.__printInformation("%s\t\t%s%s%s.tar" % (template, mirror, TEMPLATE_DIR_OPENVZ, template))
            self.__printInformation("")

            self.__printInformation("Listing remote KVM templates")
            self.__printInformation("")
            for template in kvm_remote_template_list:
                self.__printInformation("%s\t\t%s%s%s.tar" % (template, mirror, TEMPLATE_DIR_KVM , template))
            self.__printInformation("")


        except:
            print "OpenVZ and KVM templates updating and downloading failed"
            return 1
        return 0


    def runUpdate(self):
        """Update and download OpenVZ and KVM templates"""
        #Get template servers mirror list
        mirror = self.__getMirror()
        try:
            #Get OpenVZ local and remote template lists
            self.__printInformation("Fetching OPENVZ local template list")
            openvz_local_template_list = self.__getLocalTemplateList("openvz")
            self.__printInformation("Fetching OPENVZ remote template list")
            openvz_remote_template_list = self.__getRemoteTemplateList(mirror, "openvz")
            
            #Get KVM local and remote template lists
            self.__printInformation("Fetching KVM local template list")
            kvm_local_template_list = self.__getLocalTemplateList("kvm")
            self.__printInformation("Fetching KVM remote template list")
            kvm_remote_template_list = self.__getRemoteTemplateList(mirror, "kvm")

            openvz_templates = openvz_local_template_list
            kvm_templates = kvm_local_template_list

            #Remove local templates that were not selected in the lists
            openvz_download_list = self.__compareLocalRemoteTemplateList("openvz", openvz_local_template_list, openvz_templates, openvz_remote_template_list)
            kvm_download_list = self.__compareLocalRemoteTemplateList("kvm", kvm_local_template_list, kvm_templates, kvm_remote_template_list)

       	    #Update and	download KVM and OpenVZ	remote templates
            self.__downloadRemoteTemplates("openvz", mirror, openvz_download_list)
            self.__downloadRemoteTemplates("kvm", mirror, kvm_download_list)
        except:
            print "OpenVZ and KVM templates updating and downloading failed"
            return 1
        return 0


    def runGUI(self, omsInstall=False):
        """Update and download OpenVZ and KVM templates GUI"""
        #Get template servers mirror list
        mirror = self.__getMirror()
        try:
            if (not(omsInstall)):
                #Get OpenVZ local and remote template lists
                self.__printInformation("Fetching OPENVZ local template list")
                openvz_local_template_list = self.__getLocalTemplateList("openvz")
                self.__printInformation("Fetching OPENVZ remote template list")
                openvz_remote_template_list = self.__getRemoteTemplateList(mirror, "openvz")
            
                #Get KVM local and remote template lists
                self.__printInformation("Fetching KVM local template list")
                kvm_local_template_list = self.__getLocalTemplateList("kvm")
                self.__printInformation("Fetching KVM remote template list")
                kvm_remote_template_list = self.__getRemoteTemplateList(mirror, "kvm")
            else:
                #Get OpenVZ local and remote OpenNode-OMS template lists
                openvz_local_template_list = self.__getLocalTemplateList("openvz")
                if ("opennode-oms" in openvz_local_template_list):
                    openvz_local_template_list = ["opennode-oms"]
                else:
       	       	    openvz_local_template_list = []
                openvz_remote_template_list = ["opennode-oms"]

            if (not(omsInstall)):
                #Let user select OpenVZ and KVM templates to be downloaded
                openvz_templates = self.__displayTemplates("openvz", openvz_remote_template_list, openvz_local_template_list)
                kvm_templates = self.__displayTemplates("kvm", kvm_remote_template_list, kvm_local_template_list)
            else:
                #Set OpenVZ OpenNode-OMS template to be downloaded
                openvz_templates = ["opennode-oms"]

            if (not(omsInstall)):
                #Remove local templates that were not selected in the lists
                openvz_download_list = self.__compareLocalRemoteTemplateList("openvz", openvz_local_template_list, openvz_templates, openvz_remote_template_list)
                kvm_download_list = self.__compareLocalRemoteTemplateList("kvm", kvm_local_template_list, kvm_templates, kvm_remote_template_list)
            else:
                #Remove local templates that were not selected in the lists
                openvz_download_list = self.__compareLocalRemoteTemplateList("openvz", openvz_local_template_list, openvz_templates, openvz_remote_template_list)

            if (not(omsInstall)):
                #Update and download KVM and OpenVZ remote templates            
                self.__downloadRemoteTemplates("openvz", mirror, openvz_download_list)
                self.__downloadRemoteTemplates("kvm", mirror, kvm_download_list)
            else:
                #Update and download OpenVZ remote templates
                self.__downloadRemoteTemplates("openvz", mirror, openvz_download_list)
        except:
            self.__displayErrorScreen("Template(s) download failed.")
            logging.error(traceback.format_exc())
        return 0


    def __getMirror(self):
        """Return random mirror from mirrorlist"""
        #Get template servers mirror list
        mirror_web = urllib2.urlopen(MIRROR_LIST)
        mirror_list_str = mirror_web.read()
        mirror_web.close()  
        mirror_list = mirror_list_str.rstrip().lstrip().rsplit("\n")
        #Choose random mirror from list
        mirror = mirror_list[random.randrange(0,len(mirror_list),1)]
        return mirror


    def __displayErrorScreen(self, error_text="An error occurred."):
        """Display error message on error screen"""
        screen = SnackScreen()
        form = GridForm(screen, "Error occurred.", 1, 3)
        text1 = Textbox(35, 2, error_text, 0, 0)
        text2 = Textbox(35, 2, "Please try again.", 0, 0)   
        form.add(text1, 0, 0)
        form.add(text2, 0, 1)
        form.add(Button("OK"), 0, 2)
        form.runOnce()
        screen.finish()


