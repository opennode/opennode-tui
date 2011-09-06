"""OpenNode CLI Main Menu"""

from snack import SnackScreen, Button, GridForm, ButtonChoiceWindow, Textbox, Entry
import os
import time
import commands
import socket

from opennode.cli.constants import MINION_CONF
from opennode.cli import tmpldownload, tmplmake, tmpldeploy

#OpenNode Management Menu offers following options:
#    - download/list/delete templates
#    - create templates
#    - deploy templates
#    - virsh management console
#    - edit func overlord hostname


class OpenNodeUtility(object):
    """OpenNode CLI Utility"""

    def __init__(self):
        self.template_download_lib = tmpldownload.TemplateDownload()
        self.template_make_lib = tmplmake.TemplateCreate()
        self.template_deploy_lib = tmpldeploy.TemplateDeploy()


    def __displayMainScreen(self):
        """Start OpenNode utility main window"""        
        screen = SnackScreen()
        result = ButtonChoiceWindow(screen, 'OpenNode CLI', 'Welcome to the OpenNode CLI', 
                [('Exit', 'exit'), ('Console', 'console'), ('Network', 'net'), 
                ('Storage', 'storage'), ('Templates', 'templates'), ('OMS', 'oms')],
                42)
        screen.finish()
        return result


    def __displayTemplatesScreen(self):
        """Start OpenNode utility templates window"""
        screen = SnackScreen()
        result = ButtonChoiceWindow(screen, 'OpenNode Management Utility', 'Select a template action to perform', 
                [('Update list', 'update'), ('Create', 'create'), ('Deploy', 'deploy'), ('Main menu',3)]) 
        screen.finish()
        return result


    def __displayVirshScreen(self):
        """Choose virsh driver"""
        screen = SnackScreen()
        result = ButtonChoiceWindow(screen, 'OpenNode Management Utility', 'Select management console to use', 
                [('KVM', 'kvm'),('OpenVZ', 'ovz'), ('Main menu', 'back')])
        screen.finish()
        if (result == 'kvm'):
            self.__startVirshConsole('qemu:///system')
        elif (result == 'ovz'):
            self.__startVirshConsole('openvz:///system')


    def __displayOmsScreen(self):
        """Install OMS VM"""
        screen = SnackScreen()
        result = ButtonChoiceWindow(screen, 'OpenNode Management Utility', 'Select a template action to perform', 
                [('Register with OMS', 'register'), ('Download OMS','down'), ('Install OMS', 'install'),('Main menu', 'back')])
        screen.finish()
        return result

    def __startVirshConsole(self, driver='qemu:///system'):
        """Start virsh console with given driver"""
        os.system('virsh -c '+driver)


    def __displayFuncScreen(self):
        """Ask and configure Func overlord hostname in Func minion configuration"""
        #Open minion configuration file and read its content
        file = open(MINION_CONF, 'r')
        lines = file.readlines()
        file.close()
        certmaster = 'certmaster'                                             
        for line in lines:
            if (line.startswith('certmaster = ')):
                certmaster = line.split("=")[1].lstrip().rstrip()
        #New snack screen
        screen = SnackScreen()
        #Configuration form
        form = GridForm(screen, 'OpenNode Management Utility', 2, 2)
        text1 = Textbox(13, 2, "OMS address: ", 0, 0)
        entry1 = Entry(20, certmaster, 0, 0, 1, 0)
        button1 = Button('Register')
       	button2	= Button('Main menu')
        form.add(text1, 0, 0)
        form.add(entry1, 1, 0)
        form.add(button1, 0, 1)
        form.add(button2, 1, 1)
        check = True
        while (check):
            form_result = form.run()
            if (form_result == button2):
                return 0
            check = len(entry1.value().lstrip().rstrip())==0
        screen.finish()
        certmaster = entry1.value().lstrip().rstrip()

        #Calculate interface address and check /etc/hosts file for records
        hostname = commands.getoutput("hostname")

        (interface_name, interface_address) = self.__getHostRouteInterface(certmaster)

        if (not(self.__checkHostsFile(interface_address, hostname))):
            print "Adding extra ip-address and hostname pair to /etc/hosts file"
            fp = open("/etc/hosts", "a")
            fp.write("%s\t%s\n" % (interface_address, hostname))
            fp.close

        #Write results to minion configuration file
        print "Writing Func minion configuration"
        time.sleep(1)
        file = open(MINION_CONF, 'w')
        for line in lines:
            if (line.startswith('certmaster = ')):
                file.write('certmaster = '+certmaster+'\n')
            else:
                file.write(line)
        file.close()
        print "Restarting Func service"
        time.sleep(1)
        os.system('service funcd restart')
        time.sleep(1)
        return 0


    def __checkHostsFile(self, ip, hostname):
        """Check if given ip is defined for given hostname"""
        fp = open("/etc/hosts", "r")
        file_lines = fp.readlines()
        fp.close()
        for line in file_lines:
            if (not(line.rstrip().lstrip().startswith("#"))):
                line_items = line.split()
                if (line_items[0] == ip):
                    for hn in line_items[1:]:
                        if (hn == hostname):
                            return True
        return False


    def __getHostRouteInterface(self, hostname):
        """Return name and ip-address via which packets are routed to hostname"""
        certmaster_ip = self.__ipToInteger(socket.gethostbyname(hostname))

        routing_list = commands.getoutput("netstat -rn").split("\n")
        routing_list = routing_list[2:]

        ip = 0
        mask = 0

        default_interface = "vmbr0"
        used_interface = None
        interface_address = ""

        for routing_row in routing_list:
            routing_items = routing_row.split()
            if (routing_items[0] == "default"):
                default_interface = routing_items[7]
            else:
                ip = self.__ipToInteger(routing_items[0])
   	      	mask = self.__ipToInteger(routing_items[2])
       	       	if ((ip & mask) == (certmaster_ip & mask)):
                    used_interface = routing_items[7]

        if (used_interface == None):
            used_interface = default_interface

        interface_address = commands.getoutput("/sbin/ifconfig %s | grep 'inet ' | cut -d: -f2 | awk '{ print $1}'" % (used_interface))

        return (used_interface, interface_address)


    def __integerToIp(self, ip):
        """Convert integer ip address to text string"""
        address = ''
        for exp in [3,2,1,0]:
                address = address + str(ip / ( 256 ** exp )) + "."
                ip = ip % ( 256 ** exp )
        return address.rstrip('.')


    def __ipToInteger(self, ip):
        """Convert text string to integer ip address"""
        exp = 3
        int_ip = 0
        for quad in ip.split('.'):
                int_ip = int_ip + (int(quad) * (256 ** exp))
                exp = exp - 1
        return int_ip


    def deleteTemplate(self, hypervizor, template):
       	"""Delete template archive, file system files and its configuration file"""
       	return self.template_download_lib.deleteTemplate(hypervizor, template)


    def getTemplateList(self, hypervizor):
        """Get list of templates on OpenNode server"""
        return self.template_download_lib.getTemplateList(hypervizor)


    def run(self, action = 'cli'):
        """Run OpenNode utility"""
        os.system("clear")
        try:
            if (action == 'cli'):
                self.runCLI()
            elif (action == 'lib_update'):
                self.template_download_lib.runUpdate()
            elif (action == 'lib_list'):
                self.template_download_lib.runList()
            else:
                self.run()
        except:
            raise
            print "Unknown OpenNode utility action"


    def runCLI(self):
        """Run OpenNode GUI utility"""
        result = None
        while result != 'exit':
            result = self.__displayMainScreen()

            if result == 'templates':
                template_selection = self.__displayTemplatesScreen()
                if template_selection == 'update':
                    self.template_download_lib.runGUI()
                elif template_selection == 'create':
                    self.template_make_lib.run()
                elif template_selection == 'deploy':
                    self.template_deploy_lib.run()

            elif (result == 'console'):
                self.__displayVirshScreen()

            elif (result == 'oms'):
                oms_selection = self.__displayOmsScreen()
                if (oms_selection == 0):
                    self.template_download_lib.runGUI(True)
                elif (oms_selection == 1):
                    self.template_deploy_lib.run(True)

