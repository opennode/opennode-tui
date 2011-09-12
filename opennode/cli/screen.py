#!/usr/bin/env python
"""OpenNode Terminal User Interface (TUI)"""

from snack import SnackScreen, ButtonChoiceWindow, Entry, EntryWindow, ListboxChoiceWindow, CheckboxTree
from snack import snackArgs, GridFormHelp, TextboxReflowed, ButtonBar

from opennode.cli import actions

VERSION = '1.0.1'
TITLE='OpenNode TUI v%s' % VERSION


class OpenNodeTUI(object):

    def menu_exit(self):
        pass

    def display_main_screen(self):
        logic = {'exit': self.menu_exit,
                 'console': self.display_console_menu,
                 'net': self.display_network,
                 'storage': self.display_storage,
                 'oms': self.display_oms,
                 'templates': self.display_templates
                 }

        result = ButtonChoiceWindow(self.screen, TITLE, 'Welcome to the OpenNode TUI', \
                [('Exit', 'exit'),
                ('Console', 'console'),
                ('Network', 'net'),
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

    def display_storage(self):
        pass

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
        pass

    def display_oms_install(self):
        pass

    def display_templates(self):
        logic = { 'main': self.display_main_screen,
                  'list': self.display_template_repo_list,
                  'create': self.display_template_create,
                  'deploy': self.display_template_deploy,
                }

        result = ButtonChoiceWindow(self.screen, TITLE , 'Select a template action to perform',
                        [('List templates', 'list'), ('Create from running VM', 'create'), 
                         ('Deploy new VM', 'deploy'), ('Main menu', 'main')])

        logic[result]()

    def display_template_repo_list(self):       
        repos = actions.templates.get_template_repos()
        if len(repos) > 0:
            action, repo = ListboxChoiceWindow(self.screen, TITLE, 'Select the VM repository', repos, ['Ok', 'Back'])
            if action == 'back':
                self.display_templates()
            else: # enter or ok button pressed
                self.display_template_list(repo)
        else:
            ButtonChoiceWindow(self.screen, TITLE, 'Sorry, there are no configured repositories.', ['Back'])
            # no other option but to go Back
            self.display_templates()


    def display_template_list(self, repo):
        templates = actions.templates.get_template_list(repo)


    def display_template_create(self):
        pass

    def display_template_deploy(self):
        pass

    def run(self):
        """Main loop of the TUI"""
        self.screen = SnackScreen()
        self.display_main_screen()
        self.screen.finish()

if __name__ == "__main__":
    tui = OpenNodeTUI()
    tui.run()
