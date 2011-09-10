#!/usr/bin/env python
"""OpenNode Terminal User Interface (TUI)"""

from snack import SnackScreen, Button, GridForm, ButtonChoiceWindow, Textbox, Entry, EntryWindow

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

    def display_oms_register(self):
        entry_text = actions.oms.get_oms_server() # config = ConfigParser.RawConfigParser()

        command, oms_address = EntryWindow(self.screen, TITLE, 'Please, enter OMS address', ['OMS address'], 
                buttons = [('Register', 'register'), ('Back to the OMS menu', 'oms_menu')])
        if command == 'oms_menu': 
            self.display_oms()
        elif command == 'register':
            if actions.oms.validate(oms_address[0]):
                actions.oms.register(oms_address[0])


    def display_oms_download(self):
        pass

    def display_oms_install(self):
        pass

    def display_templates(self):
        pass

    def run(self):
        """Main loop of the TUI"""
        self.screen = SnackScreen()
        self.display_main_screen()
        self.screen.finish()

if __name__ == "__main__":
    tui = OpenNodeTUI()
    tui.run()
