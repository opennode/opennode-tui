#!/usr/bin/env python
"""OpenNode Terminal User Interface (TUI)"""

import os

from ovf.OvfFile import OvfFile
from snack import SnackScreen, ButtonChoiceWindow, Entry, EntryWindow

from opennode.cli.helpers import (display_create_template, display_checkbox_selection, 
                                  display_selection, display_vm_type_select, display_info)
from opennode.cli import actions
from opennode.cli.config import c
from opennode.cli.forms import KvmForm, OpenvzForm, OpenvzTemplateForm, KvmTemplateForm

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
        local_templates = actions.templates.get_local_templates(c(repo, 'type'), storage_pool)
        list_items = [('(r)' + tmpl, tmpl, tmpl in local_templates) for tmpl in remote_templates]
        purely_local_templates = list(set(local_templates) - set(remote_templates))
        list_items.extend([('(l)' + tmpl, tmpl, tmpl in local_templates) for tmpl in purely_local_templates])
        return display_checkbox_selection(self.screen, TITLE, list_items, 
                        'Please, select templates to keep in the storage pool (r - remote, l - local):')

    def display_select_template_from_storage(self, storage_pool, vm_type):
        """Displays a list of templates from a specified storage pool"""
        templates = actions.templates.get_local_templates(vm_type, storage_pool)
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
        
        # pick an instance
        action, vm_name, new_templ_name = display_create_template(self.screen, TITLE, vm_type, instances)
        if action == 'back':
            return self.display_templates()
        
        # extract active template settings
        template_settings = vm.get_active_template_settings(vm_name, storage_pool)
        template_settings["template_name"] = new_templ_name
        template_settings["vm_name"] = vm_name
        
        if vm_type == "openvz":
            form = OpenvzTemplateForm(self.screen, TITLE, template_settings)
        elif vm_type == "kvm":
            form = KvmTemplateForm(self.screen, TITLE, template_settings)
        else:
            raise ValueError, "Vm '%s' is not supported" % template_settings["vm_type"]
        
        # get user settings
        user_settings = self._display_template_create_settings(form, template_settings)
        if not user_settings:
            return self.display_main_screen()
        template_settings.update(user_settings)
        self.screen.finish()
        
        # pack template
        vm.save_as_ovf(template_settings, storage_pool)
        self.screen = SnackScreen()
        return self.display_templates()
    
    def _display_template_create_settings(self, form, template_settings):
        while 1:
            if not form.display():
                return None
            if form.validate():
                settings = template_settings.copy()
                settings.update(form.data)
                return settings
            else:
                errors = form.errors
                key, msg = errors[0] 
                display_info(self.screen, TITLE, msg, width=75)
                continue
    
    def display_vm_create(self):
        storage_pool = actions.storage.get_default_pool()
        if storage_pool is None:
            display_info(self.screen, "Error", "Default storage pool is not defined!")
            return self.display_main_screen()
        
        vm_type = display_vm_type_select(self.screen, TITLE) 
        if vm_type is None: return self.display_main_screen()
        
        template = self.display_select_template_from_storage(storage_pool, vm_type)
        if template is None: 
            return self.display_vm_create()
        
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
        user_settings = self.display_template_settings(template_settings)
        if not user_settings:
            return self.display_main_screen()
        # deploy
        self.screen.finish()
        vm.deploy(user_settings, storage_pool)
        self.screen = SnackScreen()
        return self.display_main_screen()

    def display_template_settings(self, template_settings):
        """ Display configuration details of new VM """
        vm_type = template_settings["vm_type"]
        if vm_type == "openvz":
            form = OpenvzForm(self.screen, TITLE, template_settings)
        elif vm_type == "kvm":
            form = KvmForm(self.screen, TITLE, template_settings)
        else:
            raise ValueError, "Unsupported vm type '%s'" %  vm_type
        while 1:
            if not form.display():
                return None
            if form.validate():
                settings = template_settings.copy()
                settings.update(form.data)
                return settings
            else:
                errors = form.errors
                key, msg = errors[0] 
                display_info(self.screen, TITLE, msg, width=75)
                continue
            
    def display_template_min_max_errors(self, errors):
        msg = "\n".join("* " + error for error in errors)
        self.__displayInfoScreen(msg, 70)
    
    def assure_env_sanity(self):
        """Double check we have everything needed for running TUI"""
        actions.storage.prepare_storage_pool()
    
    def run(self):
        """Main loop of the TUI"""
        self.screen = SnackScreen()
        try:
            self.assure_env_sanity()
            self.display_main_screen()
        finally:
            self.screen.finish()

if __name__ == "__main__":
    tui = OpenNodeTUI()
    tui.run()
