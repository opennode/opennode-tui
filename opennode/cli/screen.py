#!/usr/bin/env python
"""OpenNode Terminal User Interface (TUI)"""

import os

from ovf.OvfFile import OvfFile
from snack import (SnackScreen, ButtonChoiceWindow, Entry, EntryWindow,
                   ListboxChoiceWindow, Textbox, Button, GridForm, Grid, Scale, Form)

from opennode.cli.helpers import (display_create_template, display_checkbox_selection, 
                                  display_selection, display_vm_type_select, display_info)
from opennode.cli import actions
from opennode.cli.config import c
from opennode.cli.actions.vm import validation

VERSION = '2.0.0a'
TITLE='OpenNode TUI v%s' % VERSION


class OpenNodeTUI(object):

    def menu_exit(self):
        pass

    def display_main_screen(self):
        logic = {'exit': self.menu_exit,
                 'console': self.display_console_menu,
                 'createvm': self.display_vm_create,
                 'net': self.display_network,
                 'storage': self.display_storage,
                 'oms': self.display_oms,
                 'templates': self.display_templates
                 }

        result = ButtonChoiceWindow(self.screen, TITLE, 'Welcome to OpenNode TUI', \
                [('Exit', 'exit'),
                ('Console', 'console'),
                ('Create VM', 'createvm'),
                ('Network', 'net'),
                ('Storage', 'storage'),
                ('Templates', 'templates'),
                ('OMS', 'oms')],
                42)

        logic[result]()

    def display_console_menu(self):
        logic = {
               'kvm': actions.console.run_kvm,
               'ovz': actions.console.run_openvz,
               }
        result = ButtonChoiceWindow(self.screen, TITLE, 'Select a management console to use:',
                  [('KVM', 'kvm'),('OpenVZ', 'ovz'), ('Main menu', 'main')])
        if result != 'main':
            self.screen.finish()
            logic[result]()
            self.screen = SnackScreen()
        else:
            return self.display_main_screen()

    def display_storage(self):
        logic = {'main': self.display_main_screen,
                'default': self.display_storage_default,
                'add': self.display_storage_add,
                'delete': self.display_storage_delete,
               }
        result = ButtonChoiceWindow(self.screen, TITLE, 'Select storage operation',
                  [('Select default storage pool', 'default'),('Add a storage pool', 'add'),
                    ('Delete a storage pool', 'delete'), ('Main menu', 'main')])
        logic[result]()

    def display_storage_default(self):
        pool = self.display_select_storage_pool(None)
        if pool is not None:
            actions.storage.set_default_pool(pool)
        return self.display_storage()
    
    def display_storage_add(self):
        storage_entry = Entry(30, 'new')
        command, _ = EntryWindow(self.screen, TITLE, 'Please, enter a new storage pool name', 
                [('Storage pool', storage_entry),], 
                buttons = [('Add', 'add'), ('Back', 'storage')])
        if command == 'storage': 
            return self.display_storage()
        elif command == 'add':
            storage_pool = storage_entry.value().strip()
            if len(storage_pool) == 0:
                # XXX better validation
                return self.display_storage()
            actions.storage.add_pool(storage_pool)
            return self.display_storage()
        
    def display_storage_delete(self):
        pool = self.display_select_storage_pool(default=None)
        if pool is not None:
            result = ButtonChoiceWindow(self.screen, TITLE , 'Are you sure you want to delete "%s"?' %pool,
                        [('Yes, delete the pool and all of its contents', 'yes'), ('No, not today.', 'no')])
            if result == 'yes':
                # sorry, pool, time to go
                actions.storage.delete_pool(pool)
        return self.display_storage()
    
    def display_network(self):
        logic = {'main': self.display_main_screen,
                'bridge': self.display_network_bridge,
               }
        result = ButtonChoiceWindow(self.screen, TITLE, 'Select network operation',
                  [('Bridge management', 'bridge'),
                   #('Nameserver configuration', 'nameserver'), 
                   #('Hostname modification', 'hostname'), 
                    ('Main menu', 'main')])
        logic[result]()

    def display_network_bridge(self):
        logic = {'main': self.display_network,
                'add': self.display_network_bridge_add_update,
                'del': self.display_network_bridge_delete,
               }
        result = ButtonChoiceWindow(self.screen, TITLE, 'Select bridge operation',
                  [('Add new bridge', 'add'),
                   ('Delete bridge', 'del'), 
                   ('Main menu', 'main')])
        logic[result]()

    def display_network_bridge_add_update(self, bridge = None):
        action, bridge = EntryWindow(self.screen, TITLE, 'Add new bridge', 
                ['Name', 'Hello', 'FD', 'STP'],
                buttons = ['Create', 'Back'])
        if action == 'create':
            actions.network.add_bridge(bridge[0])
            actions.network.configure_bridge(bridge[0], bridge[1], bridge[2], bridge[3])
        return self.display_network_bridge()

    def display_network_bridge_delete(self):
        bridges = actions.network.list_bridges()
        if bridges is None:
            display_info(self.screen, "Error", "No network bridges found.")
            return self.display_network_bridge()
        chosen_bridge = display_selection(self.screen, TITLE, bridges, 'Please select the network bridge for modification:')
        if chosen_bridge is not None:
            result = ButtonChoiceWindow(self.screen, TITLE , 'Are you sure you want to delete "%s"?' %chosen_bridge,
                        [('Yes, delete the bridge.', 'yes'), ('No, not today.', 'no')])
            if result == 'yes':
                # sorry, pool, time to go
                actions.network.delete_bridge(chosen_bridge)
        return self.display_network_bridge()

    def display_select_storage_pool(self, default = c('general', 'default-storage-pool')):
        storage_pools = [("%s (%s)"  %(p[0], p[1]), p[0]) for p in actions.storage.list_pools()]
        return display_selection(self.screen, TITLE, storage_pools, 'Select a storage pool to use:', default = default)

    def display_oms(self):
        storage_pool = actions.storage.get_default_pool()
        if storage_pool is None:
            display_info(self.screen, "Error", "Default storage pool is not defined!")
            return self.display_main_screen()
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
        display_info(self.screen, "Error", "Not yet implemented....")
        return self.display_oms()

    def display_templates(self):
        storage_pool = actions.storage.get_default_pool()
        if storage_pool is None:
            display_info(self.screen, "Error", "Default storage pool is not defined!")
            return self.display_main_screen()
        
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
        storage_pool = actions.storage.get_default_pool()
        if storage_pool is None:
            return display_info(self.screen, "Error", "Default storage pool is not defined!")
        repos = actions.templates.get_template_repos()
        if repos is None:
            return self.display_templates()
        chosen_repo = display_selection(self.screen, TITLE, repos, 'Please, select template repository from the list')
        if chosen_repo is None:
            return self.display_templates()
        selected_list = self.display_select_template_from_repo(chosen_repo, storage_pool)
        if selected_list is None:
            return self.display_templates()
        
        from opennode.cli.helpers import DownloadMonitor
        dm = DownloadMonitor(self.screen, TITLE, len(selected_list))  
        actions.templates.sync_storage_pool(storage_pool, chosen_repo, selected_list, dm)
        self.screen.popWindow()
        self.display_templates()

    def display_select_template_from_repo(self, repo, storage_pool = c('general', 'default-storage-pool')): 
        remote_templates = actions.templates.get_template_list(repo)
        local_templates = actions.templates.get_local_templates(storage_pool, c(repo, 'type'))
        list_items = [(tmpl, tmpl, tmpl in local_templates) for tmpl in remote_templates]
        return display_checkbox_selection(self.screen, TITLE, list_items, 'Please, select templates for synchronisation')

    def display_select_template_from_storage(self, storage_pool, vm_type):
        """Displays a list of templates from a specified storage pool"""
        templates = actions.templates.get_local_templates(storage_pool, vm_type)
        return display_selection(self.screen, TITLE, templates, "Select a %s template from %s" % (vm_type, storage_pool))

    def display_template_create(self):
        storage_pool = actions.storage.get_default_pool()
        if storage_pool is None:
            return display_info(self.screen, "Error", "Default storage pool is not defined!")
        
        vm_type = display_vm_type_select(self.screen, TITLE)
        if vm_type is None: return self.display_main_screen()
        
        # list all available images of the selected type
        vm = actions.vm.get_module(vm_type)
        instances = vm.get_available_instances()
        if len(instances) == 0:
            display_info(self.screen, TITLE, "No suitable VMs found.")
            return self.display_templates()
        
        action, ctid, new_templ_name = display_create_template(self.screen, TITLE, vm_type, instances)
        if action == 'back':
            return self.display_templates()
        ovf_file = OvfFile(os.path.join(c("general", "storage-endpoint"),
                                        storage_pool, vm_type, "unpacked", 
                                        vm.get_template_name(ctid) + ".ovf"))
        
        def template_sanity_check(input_settings):
            def _range_check(setting_name, typecheck=float, required=True):
                val = input_settings.get(setting_name, None)
                min_val = input_settings.get("%s_min" % setting_name, None)
                max_val = input_settings.get("%s_max" % setting_name, None)
                if not val:
                    if required:
                        errors.append((setting_name, "%s is required!" % setting_name))
                    return
                else:
                    try:
                        typecheck(val)
                    except ValueError:
                        errors.append((setting_name, "%s value couldn't be converted to comparable representation. We've got %s." %(setting_name, val))) 
                if min_val and val < min_val:
                    errors.append((setting_name, "%s is less than template limits (%s < %s)." % (setting_name.capitalize(), val, min_val)))
                if max_val and val > max_val:
                    errors.append((setting_name, "%s is larger than template limits (%s > %s)." % (setting_name.capitalize(), val, max_val)))          
            errors = []
            _range_check("memory")
            _range_check("cpu", int)
            if not input_settings.get("disk"):
                errors.append(("disk", "Disk size is required."))
            else:
                try:
                    float(input_settings["disk"])
                except ValueError:
                    errors.append(("disk", "Disk size must be numeric."))
            return errors
        
        template_settings = vm.get_ovf_template_settings(ovf_file)
        vm_settings = self._display_template_create_settings_openvz(template_settings, validation.validate_settings)
        if not vm_settings:
            return self.display_main_screen()
        actions.vm.ovfutil.save_as_ovf(vm_type, vm_settings, ctid, storage_pool, new_templ_name)
        display_info(self.screen, TITLE, "Done!")
        return self.display_templates()
        
    def display_vm_create(self):
        storage_pool = actions.storage.get_default_pool()
        if storage_pool is None:
            display_info(self.screen, "Error", "Default storage pool is not defined!")
            return self.display_main_screen()
        
        vm_type = display_vm_type_select(self.screen, TITLE) 
        if vm_type is None: return self.display_main_screen()
        
        template = self.display_select_template_from_storage(storage_pool, vm_type)
        if template is None: return self.display_vm_create()
        
        # get ovf template settings
        ovf_file = OvfFile(os.path.join(c("general", "storage-endpoint"),
                                        storage_pool, vm_type, "unpacked", 
                                        template + ".ovf"))
        vm = actions.vm.get_module(vm_type)
        template_settings = vm.get_ovf_template_settings(ovf_file)
        errors = vm.adjust_setting_to_systems_resources(template_settings)
        if errors:
            display_info(self.screen, TITLE, "\n".join(errors), width=70, height=len(errors))
            return self.display_main_screen()
        
        # get user input
        user_settings = self.display_template_settings(template_settings, validation.validate_settings)
        if user_settings is None:
            return self.display_main_screen()
        # deploy
	self.screen.finish()
        vm.deploy(user_settings)
	self.screen = SnackScreen()
        display_info(self.screen, TITLE, "Template deployed successfully!")
        return self.display_main_screen()

    def display_template_settings(self, template_settings, validation_callback):
        """ Display configuration details of new VM """
        views = {
            "openvz": self._display_template_settings_openvz,
            "kvm": self._display_template_settings_kvm,
        }
        view = views[template_settings["vm_type"]]
        return view(template_settings, validation_callback)
    
    def _display_template_settings_kvm(self, template_settings, validation_callback):
        """ Display configuration details of new VM """
        form_rows = []
	
        input_hostname = Entry(20, template_settings.get("hostname", ''))
        form_rows.append((Textbox(20, 1, "Hostname:", 0, 0), input_hostname))

        input_memory = Entry(20, template_settings["memory"])
        form_rows.append((Textbox(20, 1, "Memory size (GB):", 0, 0), input_memory))
        
        form_rows.append((Textbox(20, 1, "Memory min/max:", 0, 0), 
                          Textbox(20, 1, "%s / %s" % (template_settings["memory_min"], 
                                                      template_settings["memory_max"]), 0, 0)))
        
        input_cpu = Entry(20, template_settings["vcpu"])
        form_rows.append((Textbox(20, 1, "Number of CPUs:", 0, 0), input_cpu))
        
        text_cpu_bounds_value = Textbox(20, 1, "%s / %s" % (template_settings["vcpu_min"], 
                                                            template_settings["vcpu_max"]), 0, 0)
        form_rows.append((Textbox(20, 1, "CPU number min/max:", 0, 0), text_cpu_bounds_value))

        button_save = Button("Save VM settings")
        button_exit = Button("Main menu")
        
        form_rows.append((button_save, button_exit))
        
        def _display_form():
            form = GridForm(self.screen, TITLE, 2, 7)
            for i, row in enumerate(form_rows): 
                for j, cell in enumerate(row):
                    form.add(cell, j, i)
            return form.runOnce()
        
        while 1:
            # display form
            form_result = _display_form()
            
            if form_result == button_exit:
                return None
            
            # collect user input
            input_settings = {
                "memory": input_memory.value().strip(),  
                "vcpu": input_cpu.value().strip(),
		"hostname": input_hostname.value().strip()
            }
            
            # validate user input
            errors = validation_callback(dict(template_settings.items() + input_settings.items()))
            
            if errors:
                key, msg = errors[0] 
                display_info(self.screen, TITLE, msg)
                continue
            else:
                settings = template_settings.copy()
                settings.update(input_settings)
                return settings
    
    def _display_template_settings_openvz(self, template_settings, validation_callback):
        form_rows = []
        
        input_memory = Entry(20, template_settings["memory"])
        form_rows.append((Textbox(20, 1, "Memory size (GB):", 0, 0), input_memory))
        
        form_rows.append((Textbox(20, 1, "Memory min/max:", 0, 0), 
                          Textbox(20, 1, "%s / %s" % (template_settings["memory_min"], 
                                                      template_settings["memory_max"]), 0, 0)))
        
        input_swap = Entry(20, template_settings["swap"])
        form_rows.append((Textbox(20, 1, "VSwap size (GB):", 0, 0), input_swap))
        
        form_rows.append((Textbox(20, 1, "VSwap min/max:", 0, 0), 
                          Textbox(20, 1, "%s / %s" % (template_settings["swap_min"], 
                                                      template_settings["swap_max"]), 0, 0)))
        
        input_cpu = Entry(20, template_settings["vcpu"])
        form_rows.append((Textbox(20, 1, "Number of CPUs:", 0, 0), input_cpu))
        
        text_cpu_bounds_value = Textbox(20, 1, "%s / %s" % (template_settings["vcpu_min"], 
                                                            template_settings["vcpu_max"]), 0, 0)
        form_rows.append((Textbox(20, 1, "CPU number min/max:", 0, 0), text_cpu_bounds_value))
        
        input_cpu_limit = Entry(20, template_settings["vcpulimit"])
        form_rows.append((Textbox(20, 1, "CPU usage limit (%):", 0, 0), input_cpu_limit))
        
        form_rows.append((Textbox(20, 1, "CPU usage min/max:", 0, 0), 
                          Textbox(20, 1, "%s / %s" % (template_settings["vcpulimit_min"], 
                                                      template_settings["vcpulimit_max"]), 0, 0)))
        
        input_disk_size = Entry(20, template_settings["disk"])
        form_rows.append((Textbox(20, 1, "Disk size (GB):", 0, 0), input_disk_size))
        
        form_rows.append((Textbox(20, 1, "Disk size min/max:", 0, 0),
                          Textbox(20, 1,  "%s / %s" % (template_settings["disk_min"], 
                                                      template_settings["disk_max"]), 0, 0)))
       
        input_hostname = Entry(20, template_settings.get("hostname", ''))
        form_rows.append((Textbox(20, 1, "Hostname:", 0, 0), input_hostname))

        input_ip = Entry(20, template_settings["ip_address"])
        form_rows.append((Textbox(20, 1, "IP-address:", 0, 0), input_ip))
        
        input_nameserver = Entry(20, template_settings["nameserver"])
        form_rows.append((Textbox(20, 2, "Nameserver:", 0, 0), input_nameserver))
        
        #ToDo: VETH support
        #text13 = Textbox(20, 2, "Use VETH:", 0, 0)
        
        input_password = Entry(20, template_settings["passwd"], password = 1)
        form_rows.append((Textbox(20, 1, "Root password:", 0, 0), input_password))
        
        input_password2 = Entry(20, template_settings["passwd"], password = 1)
        form_rows.append((Textbox(20, 2, "Root password x2:", 0, 0), input_password2))
        
        button_save = Button("Save VM settings")
        button_exit = Button("Main menu")
        form_rows.append((button_save, button_exit))
        
        def _display_form():
            form = GridForm(self.screen, TITLE, 2, 16)
            for i, row in enumerate(form_rows): 
                for j, cell in enumerate(row):
                    form.add(cell, j, i)
            return form.runOnce()
        
        while True:
            # display form
            form_result = _display_form()
            
            if form_result == button_exit:
                return None
            
            # collect user input
            input_settings = {
                "memory": input_memory.value(),  
                "swap": input_swap.value(), 
                "vcpu": input_cpu.value(),
                "vcpulimit": input_cpu_limit.value(),
                "disk": input_disk_size.value(),
                "hostname": input_hostname.value(),
     	        "ip_address": input_ip.value(),
                "nameserver": input_nameserver.value(),
                "passwd": input_password.value(),
                "passwd2": input_password2.value(),
            }
            
            # validate user input
            errors = validation_callback(dict(template_settings.items() + input_settings.items()))
            
            if errors:
                key, msg = errors[0] 
                display_info(self.screen, TITLE, msg)
                continue
            else:
                settings = template_settings.copy()
                settings.update(input_settings)
                return settings
            
    def _display_template_create_settings_openvz(self, template_settings, validation_callback):
        ts = template_settings
        form_rows = []
        # memory
        input_memory = Entry(20, ts["memory"])
        form_rows.append((Textbox(20, 1, "Memory size (GB):", 0, 0), input_memory))
        
        input_memory_min = Entry(20, ts.get("memory_min", ""))
        form_rows.append((Textbox(20, 1, "Min memory size (GB):", 0, 0), input_memory_min))
        
        input_memory_max = Entry(20, ts.get("memory_max", ""))
        form_rows.append((Textbox(20, 1, "Max memory size (GB):", 0, 0), input_memory_max))
        
        # cpu
        input_cpu = Entry(20, ts["vcpu"])
        form_rows.append((Textbox(20, 1, "Number of CPUs:", 0, 0), input_cpu))
        
        input_cpu_min = Entry(20, ts["vcpu"])
        form_rows.append((Textbox(20, 1, "Min number of CPUs:", 0, 0), input_cpu_min))
        
        input_cpu_max = Entry(20, ts["vcpu"])
        form_rows.append((Textbox(20, 1, "Max number of CPUs:", 0, 0), input_cpu_max))
        
        # disk
        input_disk_size = Entry(20, ts["disk"])
        form_rows.append((Textbox(20, 1, "Disk size (GB):", 0, 0), input_disk_size))
        
        button_save, button_exit = Button("Save VM settings"), Button("Main menu")
        form_rows.append((button_save, button_exit))
        
        def _display_form():
            form = GridForm(self.screen, TITLE, 2, 8)
            for i, row in enumerate(form_rows): 
                for j, cell in enumerate(row):
                    form.add(cell, j, i)
            return form.runOnce()
        
        while True:
            # display form
            form_result = _display_form()
            
            if form_result == button_exit:
                return None
            
            # collect user input
            input_settings = {
                "memory": input_memory.value(),
                "memory_min": input_memory_min.value(),
                "memory_max": input_memory_max.value(),
                "cpu": input_cpu.value(),
                "cpu_min": input_cpu_min.value(),
                "cpu_max": input_cpu_max.value(),
                "disk": input_disk_size.value(),
            }
            
            # validate user input
            errors = validation_callback(dict(template_settings.items() + input_settings.items()),
                                         ["memory", "cpu", "disk"])
            
            if errors:
                key, msg = errors[0] 
                display_info(self.screen, TITLE, msg)
                continue
            else:
                settings = template_settings.copy()
                settings.update(input_settings)
                return settings
    
    def display_template_min_max_errors(self, errors):
        msg = "\n".join("* " + error for error in errors)
        self.__displayInfoScreen(msg, 70)
        
    
    def run(self):
        """Main loop of the TUI"""
        self.screen = SnackScreen()
        try:
            self.display_main_screen()
        finally:
            self.screen.finish()

if __name__ == "__main__":
    tui = OpenNodeTUI()
    tui.run()
