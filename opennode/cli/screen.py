#!/usr/bin/env python
"""OpenNode Terminal User Interface (TUI)"""

import os
from uuid import uuid4

from snack import SnackScreen, ButtonChoiceWindow, Entry, EntryWindow, reflow

from opennode.cli.helpers import (display_create_template, display_checkbox_selection,
                                  display_selection, display_vm_type_select, display_info,
                                  display_template_edit_form)
from opennode.cli import actions
from opennode.cli.config import get_config
from opennode.cli.forms import (KvmForm, OpenvzForm, OpenvzTemplateForm, KvmTemplateForm,
                                OpenvzModificationForm, OpenVZMigrationForm)
from opennode.cli.actions.utils import (test_passwordless_ssh, setup_passwordless_ssh,
                                        TemplateException, CommandException, calculate_hash,
                                        save_to_tar)
from opennode.cli.actions.vm.ovfutil import save_cpu_mem_to_ovf

from ovf.OvfFile import OvfFile
from libvirt import libvirtError

VERSION = '2.0.0a'
TITLE = 'OpenNode TUI v%s' % VERSION


class OpenNodeTUI(object):

    def menu_exit(self):
        pass

    def display_main_screen(self):
        logic = {'exit': self.menu_exit,
                 'console': self.display_console_menu,
                 'createvm': self.display_vm_create,
                 'manage': self.display_manage,
                 'oms': self.display_oms,
                 }

        result = ButtonChoiceWindow(self.screen, TITLE, 'Welcome to OpenNode TUI', \
                [('Exit', 'exit', 'F12'),
                ('Console', 'console'),
                ('Create VM', 'createvm'),
                ('Manage', 'manage'),
                # XXX disable till more sound functionality
                ('OMS (beta)', 'oms')
                ],
                42)
        return logic[result]()

    def display_manage(self):
        logic = {'back': self.display_main_screen,
                 'managevm': self.display_vm_manage,
                 'net': self.display_network,
                 'storage': self.display_storage,
                 'templates': self.display_templates
                 }

        result = ButtonChoiceWindow(self.screen, TITLE, 'What would you like to manage today?',
                [('Menu', 'back', 'F12'),
                # XXX disable till more sound functionality
                #('Network', 'net'),
                ('VMs', 'managevm'),
                ('Storage', 'storage'),
                ('Templates', 'templates'),
                #('Monitoring', 'monitoring'),
                ],
                42)

        return logic[result]()

    def display_console_menu(self):
        logic = {
               'kvm': actions.console.run_kvm,
               'ovz': actions.console.run_openvz,
               }
        result = ButtonChoiceWindow(self.screen, TITLE,
                                    'Select a management console to use:',
                                    [('Menu', 'main', 'F12'),
                                     ('KVM', 'kvm'), ('OpenVZ', 'ovz')])
        if result != 'main':
            self.screen.finish()
            logic[result]()
            self.screen = SnackScreen()
            self.screen.pushHelpLine("  <Tab>/<Alt-Tab> between elements   |  <Space> selects   |  <F12> Back / exit ")
            return self.display_console_menu()
        else:
            return self.display_main_screen()

    def display_storage(self):
        logic = {'back': self.display_manage,
                'default': self.display_storage_default,
                'add': self.display_storage_add,
                'delete': self.display_storage_delete,
                'shared': self.display_storge_shared,
               }
        result = ButtonChoiceWindow(self.screen, TITLE, 'Select storage pool operation',
                  [('Back', 'back', 'F12'),
                   ('Select default', 'default'),
                   ('Add', 'add'),
                   ('Delete', 'delete')])
        logic[result]()

    def display_storage_default(self):
        pool = self.display_select_storage_pool(None)
        if pool is not None:
            actions.storage.set_default_pool(pool)
        return self.display_storage()

    def display_storge_shared(self):
        result = ButtonChoiceWindow(self.screen, TITLE, 'Select bind mount operation',
                  [('Back', 'main', 'F12'), ('List bind mounts', 'default'),
                   ('Add a bind mount', 'add'), ('Delete a bind mount', 'delete')])

    def display_storage_add(self):
        storage_entry = Entry(30, 'new')
        command, _ = EntryWindow(self.screen, TITLE,
                                 'Please, enter a new storage pool name',
                                 [('Storage pool', storage_entry)],
                                 buttons=[('Back', 'storage', 'F12'), ('Add', 'add')])
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
            result = ButtonChoiceWindow(self.screen, TITLE,
                                        'Are you sure you want to delete "%s"?' % pool,
                                        [('No, not today.', 'no', 'F12'),
                                         ('Yes, delete the pool and all of its contents', 'yes')])
            if result == 'yes':
                # sorry, pool, time to go
                try:
                    actions.storage.delete_pool(pool)
                except Exception as e:
                    err = reflow(e.message, 50)
                    self.screen = SnackScreen()
                    display_info(self.screen, TITLE, err[0], width=err[1], height=err[2])
        return self.display_storage()

    def display_network(self):
        logic = {'main': self.display_main_screen,
                'bridge': self.display_network_bridge,
               }
        result = ButtonChoiceWindow(self.screen, TITLE, 'Select network operation',
                  [('Back', 'main', 'F12'),
                   #('Nameserver configuration', 'nameserver'),
                   #('Hostname modification', 'hostname'),
                    ('Bridge management', 'bridge')])
        logic[result]()

    def display_network_bridge(self):
        logic = {'main': self.display_network,
                'add': self.display_network_bridge_add_update,
                'del': self.display_network_bridge_delete,
               }
        result = ButtonChoiceWindow(self.screen, TITLE, 'Select bridge operation',
                  [('Main menu', 'main', 'F12'),
                   ('Delete bridge', 'del'),
                   ('Add new bridge', 'add')])
        logic[result]()

    def display_network_bridge_add_update(self, bridge=None):
        action, bridge = EntryWindow(self.screen, TITLE, 'Add new bridge',
                ['Name', 'Hello', 'FD', 'STP'],
                buttons=[('Back', 'back', 'F12'), 'Create'])
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
            result = ButtonChoiceWindow(self.screen, TITLE,
                                        'Are you sure you want to delete "%s"?' %
                                        chosen_bridge,
                        [('No, not today.', 'no', 'F12'), ('Yes, delete the bridge.', 'yes')])
            if result == 'yes':
                # sorry, pool, time to go
                actions.network.delete_bridge(chosen_bridge)
        return self.display_network_bridge()

    def display_select_storage_pool(self, default=None):
        if not default:
            default = get_config().getstring('general', 'default-storage-pool')
        storage_pools = [("%s (%s)" % (p[0], p[1]), p[0]) for p in actions.storage.list_pools()]
        return display_selection(self.screen, TITLE, storage_pools,
                                 'Select a storage pool to use:',
                                 default=default)

    def display_oms(self):
        storage_pool = actions.storage.get_default_pool()
        if storage_pool is None:
            display_info(self.screen, "Error", "Default storage pool is not defined!")
            return self.display_main_screen()
        logic = {'main': self.display_main_screen,
                 'register': self.display_oms_register,
                 'download': self.display_oms_download,
                 'install': self.display_oms_install,
                }
        result = ButtonChoiceWindow(self.screen, TITLE, 'OpenNode Management Service (OMS) operations',
            [('Menu', 'main', 'F12'), ('Download OMS image', 'download'),
             ('Install OMS image', 'install'), ('Register with OMS', 'register')])
        logic[result]()

    def display_oms_register(self, msg='Please, enter OMS address and port'):
        oms_server, oms_port = actions.oms.get_oms_server()
        oms_entry_server = Entry(30, oms_server)
        oms_entry_port = Entry(30, str(oms_port))
        command, oms_address = EntryWindow(self.screen, TITLE, msg,
                                [('OMS server address', oms_entry_server),
                                 ('OMS server port', oms_entry_port)],
                                buttons=[('Back', 'oms_menu', 'F12'),
                                         ('Register', 'register')])
        if command == 'oms_menu':
            return self.display_oms()
        elif command == 'register':
            server = oms_entry_server.value().strip()
            port = oms_entry_port.value().strip()
            if actions.network.validate_server_addr(server, port):
                self.screen.finish()
                actions.oms.register_oms_server(server, port)
                self.screen = SnackScreen()
                return self.display_oms()
            else:
                # XXX: error handling?
                return self.display_oms_register("Error: Cannot resolve OMS address/port")

    def display_oms_download(self):
        result = ButtonChoiceWindow(self.screen, TITLE,
                                    'Would you like to download OMS template?',
                                    [('No', 'main', 'F12'), ('Yes', 'download')])
        if result == 'download':
            self.screen.finish()
            actions.templates.sync_oms_template()
            self.screen = SnackScreen()
            display_info(self.screen, "Done", "Finished downloading OMS VM!")
        return self.display_oms()

    def display_oms_install(self):
        vm_type = 'openvz'
        template = get_config().getstring('opennode-oms-template', 'template_name')
        callback = self.display_oms
        oms_flag = {'appliance_type': 'oms'}
        return self.display_vm_create(callback, vm_type, template, custom_settings=oms_flag)

    def display_templates(self):
        storage_pool = actions.storage.get_default_pool()
        if storage_pool is None:
            display_info(self.screen, "Error", "Default storage pool is not defined!")
            return self.display_main_screen()

        logic = {'back': self.display_manage,
                 'manage': self.display_template_manage,
                 'create': self.display_template_create,
                 'edit': self.display_template_edit,
                }
        result = ButtonChoiceWindow(self.screen, TITLE,
                                    'Select a template action to perform',
                                    [('Back', 'back', 'F12'),
                                     ('Create', 'create'),
                                     ('Edit', 'edit'),
                                     ('Download', 'manage')])
        logic[result]()

    def display_template_manage(self):
        # XXX Ugly structure, needs refactoring
        if actions.templates.is_syncing():
            self.screen.finish()
            actions.utils.attach_screen('OPENNODE-SYNC')
            self.screen = SnackScreen()
        else:
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
            self.screen.finish()
            try:
                actions.templates.sync_storage_pool(storage_pool, chosen_repo, selected_list)
            except TemplateException:
                # here comes hack
                self.screen = SnackScreen()
                cleanup = ButtonChoiceWindow(self.screen, 'Existing task pool',
                                               "A task pool is already defined. It could mean\nthat the previous " +
                                               "synchronisation crashed, or that there is one working already.\n\n" +
                                               "Would you like to force synchronisation?",
                                                      ['Yes', 'No'])
                self.screen.finish()
                if cleanup == 'yes':
                    actions.templates.sync_storage_pool(storage_pool, chosen_repo, selected_list, force=True)
            self.screen = SnackScreen()
        self.display_templates()

    def display_select_template_from_repo(self, repo, storage_pool):
        remote_templates = actions.templates.get_template_list(repo)
        local_templates = actions.templates.get_local_templates(get_config().getstring(repo, 'type'),
                                                                storage_pool)
        list_items = [('(r)' + tmpl, tmpl, tmpl in local_templates) for tmpl in remote_templates]
        purely_local_templates = list(set(local_templates) - set(remote_templates))
        list_items.extend([('(l)' + tmpl, tmpl, True) for tmpl in purely_local_templates])
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
        if vm_type is None:
            return self.display_main_screen()

        # list all available images of the selected type
        vm = actions.vm.get_module(vm_type)
        instances = vm.get_available_instances()
        if len(instances) == 0:
            display_info(self.screen, TITLE,
                "No suitable VMs found. Only stopped VMs can be\nused for creating new templates!")
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
            template_settings['ostemplate'] = actions.vm.openvz.detect_os(vm_name)
            form = OpenvzTemplateForm(self.screen, TITLE, template_settings)
        elif vm_type == "kvm":
            form = KvmTemplateForm(self.screen, TITLE, template_settings)
        else:
            raise ValueError("VM type '%s' is not supported" % template_settings["vm_type"])

        # get user settings
        user_settings = self._display_custom_form(form, template_settings)
        if not user_settings:
            return self.display_main_screen()
        template_settings.update(user_settings)
        self.screen.finish()

        # pack template
        vm.save_as_ovf(template_settings, storage_pool)
        self.screen = SnackScreen()
        return self.display_templates()


    def display_template_edit(self):
        template_type = display_vm_type_select(self.screen, TITLE)
        if template_type is None:
            return self.display_templates()
        vm = actions.vm.get_module(template_type)
        template = self.display_select_template_from_storage(actions.storage.get_default_pool(),
                                                             template_type)
        if template is None:
            return self.display_templates()

        unpacked_base = os.path.join(get_config().getstring('general', 'storage-endpoint'),
                                     get_config().getstring('general', 'default-storage-pool'),
                                     template_type,
                                     'unpacked')

        ovf_file_name = os.path.join(unpacked_base, template + '.ovf')
        try:
            ovf_file = OvfFile(ovf_file_name)
        except IOError as (errno, _):
            if errno == 2:  # ovf file not found
                display_info(self.screen, "ERROR", "Template OVF file is missing:\n%s" % ovf_file_name)
            return self.display_templates()
        settings = vm.read_ovf_settings(ovf_file)

        new_values = display_template_edit_form(self.screen, TITLE, settings)

        changed = False
        rename = False
        for k in new_values:
            if k == 'template_name':
                if settings[k] != new_values[k]:
                    rename = True
            else:
                if settings[k] != new_values[k]:
                    changed = True
 
        # Protect against directory traversing
        # Take basename form new name and run with that
        new_name = os.path.basename(new_values['template_name'])
        if settings['template_name'] != new_name:
            rename = True
        if not changed and not rename:
            return self.display_templates()

        if changed:
            save_cpu_mem_to_ovf(ovf_file, new_values)
            if not rename:
                os.unlink(os.path.join(unpacked_base, '..', template + '.tar'))
                os.unlink(os.path.join(unpacked_base, '..', template + '.tar.pfff'))
                tmpl_file = os.path.join(get_config().getstring('general', 'storage-endpoint'),
                                         get_config().getstring('general', 'default-storage-pool'),
                                         template_type, template + '.tar')
                filenames = []
                filenames.append((os.path.join(unpacked_base, template + '.scripts.tar.gz'),
                                  new_name+'.scripts.tar.gz'))
                filenames.append((os.path.join(unpacked_base, template + '.tar.gz'),
                                  new_name+'.tar.gz'))
                filenames.append((os.path.join(unpacked_base, template + '.ovf'),
                                  new_name+'.ovf'))
                save_to_tar(tmpl_file, filenames)
                calculate_hash(tmpl_file)
                display_info(self.screen, TITLE, 'Template "%s"\nmetadata successfully edited.' % template, width=60, height=2)
        if rename:
            VirtualSystem = ovf_file.document.getElementsByTagName('VirtualSystem')
            VirtualSystem[0].attributes['ovf:id'].value = new_name
            References = ovf_file.document.getElementsByTagName('References')
            # TODO: until our packaged templates contain incorrect .ovf
            # we can not rely on files defined in References section
            for ref_node in References:
                file_nodes = ref_node.getElementsByTagName('File')
                for item in file_nodes:
                    if item.attributes['ovf:href'].value == template + '.tar.gz':
                        item.attributes['ovf:href'].value = new_name + '.tar.gz'
            new_ovf_fn = os.path.join(unpacked_base, new_name + '.ovf')
            with open(new_ovf_fn, 'wt') as f:
                ovf_file.writeFile(f)
            os.rename(os.path.join(unpacked_base, template + '.scripts.tar.gz'),
                      os.path.join(unpacked_base, new_name + '.scripts.tar.gz'))
            os.rename(os.path.join(unpacked_base, template + '.tar.gz'),
                      os.path.join(unpacked_base, new_name + '.tar.gz')) 
            os.unlink(os.path.join(unpacked_base, template + '.ovf'))
            os.unlink(os.path.join(unpacked_base, '..', template + '.tar'))
            os.unlink(os.path.join(unpacked_base, '..', template + '.tar.pfff'))
            tmpl_file = os.path.join(get_config().getstring('general', 'storage-endpoint'),
                                     get_config().getstring('general', 'default-storage-pool'),
                                     template_type, new_name + '.tar')
            filenames = []
            filenames.append((os.path.join(unpacked_base, new_name + '.scripts.tar.gz'),
                              new_name+'.scripts.tar.gz'))
            filenames.append((os.path.join(unpacked_base, new_name + '.tar.gz'),
                              new_name+'.tar.gz'))
            filenames.append((os.path.join(unpacked_base, new_name + '.ovf'),
                              new_name+'.ovf'))
            save_to_tar(tmpl_file, filenames)
            calculate_hash(tmpl_file)
            display_info(self.screen, TITLE, 'Renamed \"%s\" to\n\"%s\"' % (template, new_name), width=50, height=2)

        return self.display_templates()


    def _display_custom_form(self, form, template_settings):
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

    def _perform_openvz_migration(self, vm_type, vm_id):
        migration_form = OpenVZMigrationForm(self.screen, TITLE)
        while 1:
            if not migration_form.display():
                return self.display_vm_manage()
            if migration_form.validate():
                break
            else:
                errors = migration_form.errors
                key, msg = errors[0]
                display_info(self.screen, TITLE, msg, width=75)
        target_host = migration_form.data['target host']
        live = migration_form.data['live'] == 1
        vm = actions.vm.get_module(vm_type)

        if not test_passwordless_ssh(target_host):
            setup_keys = ButtonChoiceWindow(self.screen, "Passwordless SSH",
                                       "Would you like to setup passwordless SSH to %s?" % target_host,
                                              ['Yes', 'No'])
            if setup_keys == 'yes':
                self.screen.finish()
                setup_passwordless_ssh(target_host)
                print "Passwordles ssh should be working now."
                self.screen = SnackScreen()
            else:
                return self.display_vm_manage()

        self.screen.finish()
        try:
            vm.migrate(vm_id, target_host, live=live)
            self.screen = SnackScreen()
        except libvirtError as e:
            errmsg = e.get_error_message()
            err = reflow(errmsg, 50)
            self.screen = SnackScreen()
            display_info(self.screen, TITLE, err[0], width=err[1], height=err[2])
        except CommandException as e:
            errmsg = str(e)
            if e.code is not None:
                errmsg = errmsg + ' - Error code ' + str(e.code)
            err = reflow(errmsg, 50)
            self.screen = SnackScreen()
            display_info(self.screen, TITLE, err[0], width=err[1], height=err[2])

        return self.display_vm_manage()

    def display_vm_manage(self):
        storage_pool = actions.storage.get_default_pool()
        if storage_pool is None:
            return display_info(self.screen, "Error", "Default storage pool is not defined!")
        available_vms = {}
        vms_labels = []
        for vmt in actions.vm.backends():
            vms = actions.vm.list_vms(vmt)
            for vm in vms:
                available_vms[vm["uuid"]] = vm
                vms_labels.append(("%s (%s) - %s" % (vm["name"], vm["run_state"],
                                                     vm["vm_type"]), vm["uuid"]))
        res = display_selection(self.screen, TITLE, vms_labels,
                                "Pick VM for modification:",
                                buttons=[('Back', 'back', 'F12'), 'Edit', 'Start', 'Stop', 'Migrate', 'Delete'])
        if res is None:
            return self.display_manage()
        else:
            action, vm_id = res
        if action == 'back':
            return self.display_manage()

        if action == 'migrate':
            vm_type = available_vms[vm_id]["vm_type"]
            if vm_type != 'openvz':
                display_info(self.screen, TITLE, "Only OpenVZ VMs are supported at the moment, sorry.")
            else:
                return self._perform_openvz_migration(vm_type, vm_id)

        if action == 'stop':
            if available_vms[vm_id]['state'] != 'active':
                display_info(self.screen, TITLE, "Cannot stop inactive VMs!")
            else:
                self.screen.finish()
                actions.vm.shutdown_vm(available_vms[vm_id]["vm_uri"], vm_id)
                self.screen = SnackScreen()
            return self.display_vm_manage()

        if action == 'start':
            if available_vms[vm_id]['state'] != 'inactive':
                display_info(self.screen, TITLE, "Cannot start already running VM!")
            else:
                self.screen.finish()
                try:
                    actions.vm.start_vm(available_vms[vm_id]['vm_uri'], vm_id)
                    self.screen = SnackScreen()
                except libvirtError as e:
                    errmsg = e.get_error_message()
                    err = reflow(errmsg, 50)
                    self.screen = SnackScreen()
                    display_info(self.screen, TITLE, err[0], width=err[1], height=err[2])
                except CommandException as e:
                    errmsg = e
                    if e.code is not None:
                        errmsg = errmsg + ' - Error code ' + str(e.code)
                    err = reflow(errmsg, 50)
                    self.screen = SnackScreen()
                    display_info(self.screen, TITLE, err[0], width=err[1], height=err[2])
            return self.display_vm_manage()

        if action == 'delete':
            if available_vms[vm_id]['state'] != 'inactive':
                display_info(self.screen, TITLE, "Cannot delete running VM!")
            else:
                result = ButtonChoiceWindow(self.screen, TITLE,
                                        "Are you sure you want to delete VM '%s'" % available_vms[vm_id]['name'],
                                        [('No, not today.', 'no', 'F12'),
                                         ('Yes, do that.', 'yes')])

                if result == 'yes':
                    self.screen.finish()
                    actions.vm.undeploy_vm(available_vms[vm_id]['vm_uri'], vm_id)
                    self.screen = SnackScreen()
            return self.display_vm_manage()

        if action is None or action == 'edit':
            vm_type = available_vms[vm_id]['vm_type']

            if vm_type == 'openvz':
                ctid = actions.vm.openvz.get_ctid_by_uuid(vm_id)
                storage_pool = actions.storage.get_default_pool()
                vm = actions.vm.get_module(vm_type)
                template_settings = vm.get_active_template_settings(ctid, storage_pool)
                available_vms[vm_id]["memory_min"] = template_settings["memory_min"]
                available_vms[vm_id]['onboot'] = actions.vm.openvz. \
                                get_onboot(ctid)
                available_vms[vm_id]['bootorder'] = actions.vm.openvz. \
                                get_bootorder(ctid)
                available_vms[vm_id]["vcpulimit"] = actions.vm.openvz.get_cpulimit(ctid)
                available_vms[vm_id]["cpuutilization"] = actions.vm.openvz.get_vzcpucheck()
                available_vms[vm_id]["ioprio"] = actions.vm.openvz.get_ioprio(ctid)
                available_vms[vm_id]["ioprio_old"] = available_vms[vm_id]["ioprio"]
                form = OpenvzModificationForm(self.screen, TITLE, available_vms[vm_id])
            else:
                display_info(self.screen, TITLE,
                    "Editing of '%s' VMs is not currently supported." % vm_type)
                return self.display_vm_manage()

            # TODO KVM specific form
            user_settings = self._display_custom_form(form, available_vms[vm_id])

            if user_settings is None:
                return self.display_vm_manage()

            actions.vm.update_vm(available_vms[vm_id]['vm_uri'], vm_id, user_settings)

            if available_vms[vm_id]["state"] == "inactive":
                display_info(self.screen, TITLE,
                    "Note that for some settings to propagate you\nneed to (re)start the VM!")

            return self.display_vm_manage()

    def display_vm_create(self, callback=None, vm_type=None, template=None, custom_settings=None):
        if callback is None:
            callback = self.display_main_screen

        storage_pool = actions.storage.get_default_pool()
        if storage_pool is None:
            display_info(self.screen, "Error", "Default storage pool is not defined!")
            return callback()

        chosen_vm_type = vm_type if vm_type is not None else display_vm_type_select(self.screen, TITLE)
        if chosen_vm_type is None:
            return callback()

        chosen_template = (template if template is not None
                           else self.display_select_template_from_storage(storage_pool, chosen_vm_type))
        if chosen_template is None:
            return callback()

        # get ovf template setting
        try:
            path = os.path.join(get_config().getstring("general", "storage-endpoint"),
                                storage_pool, chosen_vm_type, "unpacked",
                                chosen_template + ".ovf")
            ovf_file = OvfFile(path)
        except IOError as (errno, _):
            if errno == 2:  # ovf file not found
                display_info(self.screen, "ERROR", "Template OVF file is missing:\n%s" % path)
                return callback()
        vm = actions.vm.get_module(chosen_vm_type)
        template_settings = vm.get_ovf_template_settings(ovf_file)
        errors = vm.adjust_setting_to_systems_resources(template_settings)
        if errors:
            display_info(self.screen, TITLE, "\n".join(errors), width=70, height=len(errors))
            return callback()

        # get user input
        user_settings = self.display_template_settings(template_settings)
        if not user_settings:
            return callback()
        # deploy
        self.screen.finish()
        if custom_settings:
            user_settings.update(custom_settings)
        # set uuid of the image
        user_settings['uuid'] = str(uuid4())
        vm.deploy(user_settings, storage_pool)
        self.screen = SnackScreen()
        return callback()

    def display_template_settings(self, template_settings):
        """ Display configuration details of a new VM """
        vm_type = template_settings["vm_type"]
        if vm_type == "openvz":
            template_settings["cpuutilization"] = actions.vm.openvz.get_vzcpucheck()
            form = OpenvzForm(self.screen, TITLE, template_settings)
        elif vm_type == "kvm":
            form = KvmForm(self.screen, TITLE, template_settings)
        else:
            raise ValueError("Unsupported vm type '%s'" % vm_type)
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
        self.screen.pushHelpLine("  <Tab>/<Alt-Tab> between elements   |  <Space> selects   |  <F12> Back / exit ")

        try:
            self.assure_env_sanity()
            self.display_main_screen()
        finally:
            self.screen.finish()

if __name__ == "__main__":
    tui = OpenNodeTUI()
    tui.run()
