#!/usr/bin/env python
"""OpenNode Terminal User Interface (TUI)"""
import types
from ovf.OvfFile import OvfFile
from snack import SnackScreen, ButtonChoiceWindow, Entry, EntryWindow, \
                    ListboxChoiceWindow, Textbox, Button, GridForm

from opennode.cli.helpers import SelectCheckboxWindow
from opennode.cli import actions
from opennode.cli.config import c
import os
from mailbox import FormatError
from opennode.cli.actions.vm import openvz

VERSION = '2.0.0'
TITLE='OpenNode TUI v%s' % VERSION


class OpenNodeTUI(object):

    def menu_exit(self):
        pass

    def _display_selection(self, list_of_items, subtitle, default = None):
        """Display a list of items, return selected one or None, if nothing was selected"""
        if len(list_of_items) > 0:
            if not isinstance(list_of_items[0], types.TupleType):
                # if we have a list of strings, we'd prefer to get these strings as the selection result
                list_of_items = zip(list_of_items, list_of_items)
            height = 10
            scroll = 1 if len(list_of_items) > height else 0
            action, selection = ListboxChoiceWindow(self.screen, TITLE, subtitle, list_of_items, 
                                ['Ok', 'Back'], scroll = scroll, height = height, default = default)
            if action != 'back':
                return selection
        else:
            ButtonChoiceWindow(self.screen, TITLE, 'Sorry, there are no items to choose from', ['Back'])
        return None

    def _display_checkbox_selection(self, list_of_items, subtitle):
        if len(list_of_items) > 0:            
            action, selection = SelectCheckboxWindow(self.screen, TITLE, subtitle, list_of_items, ['Ok', 'Back'], height = 10)
            if action != 'back':
                return selection
        else:
            ButtonChoiceWindow(self.screen, TITLE, 'Sorry, there are no items to choose from', ['Back'])
        return None

    def display_main_screen(self):
        logic = {'exit': self.menu_exit,
                 'console': self.display_console_menu,
                 'createvm': self.display_create_vm,
                 'net': self.display_network,
                 'storage': self.display_default_storage,
                 'oms': self.display_oms,
                 'templates': self.display_templates
                 }

        result = ButtonChoiceWindow(self.screen, TITLE, 'Welcome to the OpenNode TUI', \
                [('Exit', 'exit'),
                ('Console', 'console'),
                ('Create VM', 'createvm'),
                #('Network', 'net'),
                ('Storage', 'storage'),
                ('Templates', 'templates'),
                ('OMS', 'oms')],
                42)

        logic[result]()

    def display_console_menu(self):
        logic = {'main': self.display_main_screen,
               'kvm': actions.console.run_kvm,
               'ovz': actions.console.run_openvz,
               }
        result = ButtonChoiceWindow(self.screen, TITLE, 'Select management console to use',
                  [('KVM', 'kvm'),('OpenVZ', 'ovz'), ('Main menu', 'main')])

        logic[result]()

    def display_network(self):
        pass

    def display_default_storage(self):
        pool = self.display_select_storage_pool()
        if pool is not None:
            actions.storage.set_default_pool(pool)
        self.display_main_screen()

    def display_select_storage_pool(self):
        storage_pools = actions.storage.list_pools()
        return self._display_selection(storage_pools, 'Select the storage pool to use:', default = c('general', 'default-storage-pool'))

    def display_oms(self):
        logic = { 'main': self.display_main_screen,
                  'register': self.display_oms_register,
                  'download': self.display_oms_download,
                  'install': self.display_oms_install,
                }
        result = ButtonChoiceWindow(self.screen, TITLE, 'OpenNode Management Service (OMS) operations',
            [('Register with OMS', 'register'), ('Download OMS image','download'), 
             ('Install OMS image', 'install'), ('Main menu', 'main')])
        logic[result]()

    def display_oms_register(self, error_msg=''):
        oms_server, oms_port = actions.oms.get_oms_server()
        oms_entry_server = Entry(30, oms_server)
        oms_entry_port = Entry(30, oms_port)
        command, oms_address = EntryWindow(self.screen, TITLE, 'Please, enter OMS address\n%s'%error_msg, 
                [('OMS server address', oms_entry_server),
                 ('OMS server port', oms_entry_port)], 
                buttons = [('Register', 'register'), ('Back to the OMS menu', 'oms_menu')])
        if command == 'oms_menu': 
            self.display_oms()
        elif command == 'register':
            server = oms_entry_server.value().strip()
            port = oms_entry_port.value().strip()
            if actions.oms.validate_oms_server(server, port):
                actions.oms.register_oms_server(server, port)
                self.display_oms()
            else:
                # XXX: error handling?
                self.display_oms_register(error_msg = "Incorrect server data")

    def display_oms_download(self):
        logic = { 'main': self.display_main_screen,
                  'download': actions.templates.sync_oms_template,
                }
        result = ButtonChoiceWindow(self.screen, TITLE , 'Would you like to download OMS template?',
                        [('Yes', 'download'), ('No', 'main')])
        logic[result]()

    def display_oms_install(self):
        pass

    def display_templates(self):
        logic = { 'main': self.display_main_screen,
                  'manage': self.display_template_manage,
                  'create': self.display_template_create,
                }
        result = ButtonChoiceWindow(self.screen, TITLE , 'Select a template action to perform',
                        [('Manage template cache', 'manage'), ('Create a new template from VM', 'create'), 
                         ('Main menu', 'main')])
        logic[result]()

    def display_template_manage(self):
        # XXX Ugly structure, needs refactoring
        storage_pool = self.display_select_storage_pool()
        if storage_pool is None:
            self.display_templates()
        repos = actions.templates.get_template_repos()
        if repos is None:
            self.display_templates()
        chosen_repo = self._display_selection(repos, 'Please, select template repository from the list')
        if chosen_repo is None:
            self.display_templates()
        selected_list = self.display_select_template_from_repo(chosen_repo, storage_pool)
        if selected_list is None:
            self.display_templates()
        self.screen.finish()
        actions.templates.sync_storage_pool(storage_pool, chosen_repo, selected_list)
        self.screen = SnackScreen()
        self.display_templates()

    def display_select_template_from_repo(self, repo, storage_pool = c('general', 'default-storage-pool')): 
        remote_templates = actions.templates.get_template_list(repo)
        local_templates = actions.templates.get_local_templates(storage_pool, c(repo, 'type'))
        list_items = [(tmpl, tmpl, tmpl in local_templates) for tmpl in remote_templates]
        return self._display_checkbox_selection(list_items, 'Please, select templates for synchronisation')

    def display_select_template_from_storage(self, storage_pool, type):
        """Displays a list of templates from a specified storage pool"""
        templates = actions.templates.get_local_templates(storage_pool, type)
        return self._display_selection(templates, "Select a %s template from %s" % (type, storage_pool))

    def display_vm_type_select(self):
        """Display selection menu for the template type"""
        types = ['kvm', 'openvz']
        return self._display_selection(types, 'Select the VM type')

    def display_template_create(self):
        pass

    def display_create_vm(self):
        # first pick a storage pool
        storage_pool = self.display_select_storage_pool()
        vm_type = self.display_vm_type_select()
        template = self.display_select_template_from_storage(storage_pool, vm_type)
        
        # get ovf template settings
        ovf_file = OvfFile(os.path.join(c("general", "storage-endpoint"),
                                        storage_pool, vm_type, "unpacked", 
                                        template + ".ovf"))
        vm = actions.vm.get_module(vm_type)
        template_settings = vm.get_ovf_template_settings(ovf_file)
        errors = vm.adjust_setting_to_systems_resources(template_settings)
        if errors:
            self.__displayInfoScreen("\n".join(errors), width=70, height=len(errors))
        
        # get user input 
        user_settings = self._display_template_settings(template_settings, vm.validate_template_settings)
        print storage_pool, type, template, user_settings 

    def _display_template_settings(self, template_settings, validation_callback):
        """ Display configuration details of new VM """
        views = {
            "openvz": self._display_template_settings_openvz,
            "kvm": self._display_template_settings_kvm,
        }
        view = views[template_settings["vm_type"]]
        return view(template_settings, validation_callback)
    
    def _display_template_settings_openvz(self, template_settings, validation_callback):
        form_rows = []
        
        text_memory = Textbox(20, 1, "Memory size (GB):", 0, 0)
        input_memory = Entry(20, template_settings["memory"])
        form_rows.append((text_memory, input_memory))
        
        text_memory_bounds = Textbox(20, 1, "Memory min/max:", 0, 0)
        text_memory_bounds_value = Textbox(20, 1, "%s / %s" % (template_settings["memory_min"], template_settings["memory_max"]), 0, 0)
        form_rows.append((text_memory_bounds, text_memory_bounds_value))
        
        text_cpu = Textbox(20, 1, "Number of CPUs:", 0, 0)
        input_cpu = Entry(20, template_settings["vcpu"])
        form_rows.append((text_cpu, input_cpu))
        
        text_cpu_bounds = Textbox(20, 1, "CPU number min/max:", 0, 0)
        text_cpu_bounds_value = Textbox(20, 1, "%s / %s" % (template_settings["vcpu_min"], template_settings["vcpu_max"]), 0, 0)
        form_rows.append((text_cpu_bounds, text_cpu_bounds_value))
        
        text_cpu_limit = Textbox(20, 1, "CPU usage limit (%):", 0, 0)
        input_cpu_limit = Entry(20, template_settings["vcpulimit"])
        form_rows.append((text_cpu_limit, input_cpu_limit))
        
        text_cpu_usage_bounds = Textbox(20, 1, "CPU usage min/max:", 0, 0)
        text_cpu_usage_bounds_value = Textbox(20, 1, "%s / %s" % (template_settings["vcpulimit_min"], template_settings["vcpulimit_max"]), 0, 0)
        form_rows.append((text_cpu_usage_bounds, text_cpu_usage_bounds_value))
        
        text_disk_size = Textbox(20, 1, "Disk size (GB):", 0, 0)
        input_disk_size = Entry(20, template_settings["disk"])
        form_rows.append((text_disk_size, input_disk_size))
        
        text_disk_size_bounds = Textbox(20, 1, "Disk size min/max:", 0, 0)
        text_disk_size_bounds_value = Textbox(20, 1, "%s / %s" % (template_settings["disk_min"], template_settings["disk_max"]), 0, 0)
        form_rows.append((text_disk_size_bounds, text_disk_size_bounds_value))
        
        text_ip = Textbox(20, 1, "IP-address:", 0, 0)
        input_ip = Entry(20, template_settings["ip_address"])
        form_rows.append((text_ip, input_ip))
        
        text_nameserver = Textbox(20, 2, "Nameserver:", 0, 0)
        input_nameserver = Entry(20, template_settings["nameserver"])
        form_rows.append((text_nameserver, input_nameserver))
        
        #ToDo: VETH support
        #text13 = Textbox(20, 2, "Use VETH:", 0, 0)
        
        text_password = Textbox(20, 1, "Root password:", 0, 0)
        input_password = Entry(20, template_settings["passwd"], password = 1)
        form_rows.append((text_password, input_password))
        
        text_password2 = Textbox(20, 2, "Root password x2:", 0, 0)
        input_password2 = Entry(20, template_settings["passwd"], password = 1)
        form_rows.append((text_password2, input_password2))
        
        button_save = Button("Save VM settings")
        button_exit = Button("Main menu")
        form_rows.append((button_save, button_exit))
        
        def _display_form():
            screen = SnackScreen()
            form = GridForm(screen, "OpenNode Management Utility", 2, 14)
            for i, form_row in enumerate(form_rows): 
                for j in (0, 1):
                    form.add(form_row [j], j, i)
            result = form.run()
            screen.finish()
            return result
        
        while 1:
            # display form
            form_result = _display_form()
            
            if form_result == button_exit:
                return None
            
            # collect user input
            input_settings = {
                "memory": input_memory.value(),  
                "vcpu": input_cpu.value(),
                "vcpulimit": input_cpu_limit.value(),
                "disk": input_disk_size.value(),
                "ip_address": input_ip.value(),
                "nameserver": input_nameserver.value(),
                "passwd": input_password.value(),
                "passwd2": input_password2.value(),
            }
            
            # validate user input 
            errors = validation_callback(template_settings, input_settings)
            
            if errors:
                key, msg = errors[0] 
                self.__displayInfoScreen(msg)
                continue
            else:
                settings = template_settings
                settings.update(input_settings)
                return settings

            #ToDo: VETH support
            #if (entry9.selected()):
            #    template_settings["veth"] = "1"
            #else:
            #    template_settings["veth"] = "0"
            
    
    def _display_template_settings_kvm(self, template_settings, validator_callback):
        raise Exception, "Not implemented"
    
    def display_template_min_max_errors(self, errors):
        msg = "\n".join([ "* " + error for error in errors ])
        self.__displayInfoScreen(msg, 70)
            
    
    def __displayInfoScreen(self, info_text="Information.", width=50, height=2):
        """Display information message on information screen"""
        screen = SnackScreen()
        form = GridForm(screen, "Information.", 1, 2)
        text1 = Textbox(width, height, info_text, 0, 0)
        form.add(text1, 0, 0)
        form.add(Button("OK"), 0, 1)
        form.runOnce()
        screen.finish()
    
    def run(self):
        """Main loop of the TUI"""
        self.screen = SnackScreen()
        self.display_main_screen()
        self.screen.finish()

if __name__ == "__main__":
    tui = OpenNodeTUI()
    tui.run()
