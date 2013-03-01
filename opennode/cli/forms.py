#!/usr/bin/env python

import operator
import os
import re
import socket
from snack import Grid, Entry, Listbox, colorsets, FLAG_DISABLED, Textbox, Button
from snack import GridForm, Label, Checkbox, ButtonBar, RadioBar
from opennode.cli.actions import sysresources as sysres


class VBox(Grid):
    """ Helper wrapper around snack.Grid
    Vertical 1 column grid element. """
    def __init__(self, rows=1):
        Grid.__init__(self, 1, rows)
        self.lastrow=0
        self.rows=rows

    def append(self, widget, *args, **kwargs):
        if self.lastrow >= self.rows:
            raise Exception('Row index out of bounds')
        self.setField(widget, 0, self.lastrow, *args, **kwargs)
        self.lastrow += 1


class HBox(Grid):
    """ Helper wrapper around snack.Grid
    Horisontal 1 row grid element. """
    def __init__(self, cols=1):
        Grid.__init__(self, cols, 1)
        self.lastcol = 0
        self.cols = cols

    def append(self, widget, *args, **kwargs):
        if self.lastcol >= self.cols:
            raise Exception('Column index out of bounds')
        self.setField(widget, self.lastcol, 0, *args, **kwargs)
        self.lastcol += 1

        
class Form(object):
    errors, data = [], {}

    def __init__(self, screen, title, fields):
        self.title, self.screen, self.fields = title, screen, fields

    def validate(self):
        self.errors = reduce(operator.add, [self.fields[field].errors for field in self.fields
                                            if not self.fields[field].validate()], [])
        if not self.errors:
            self.data = dict([(self.fields[field].name, self.fields[field].value()) for field in self.fields])
            return True
        else:
            return False

    def display(self):
        pass


class CreateVM(Form):
    def __init__(self, screen, title, settings):
        self.fields = {}
        self.labels = {}
        self.fields['memory'] = FloatField('memory',
                                           settings.get('memory', ''),
                                           settings.get('memory_min', ''),
                                           settings.get('memory_max', ''),
                                           width=6)
        self.fields['swap'] = FloatField('swap',
                                         settings.get('swap', ''),
                                         settings.get('swap_min', ''),
                                         settings.get('swap_max', ''),
                                         width=6)
        self.fields['disk'] = FloatField('disk',
                                         settings.get('disk', ''),
                                         settings.get('disk_min', ''),
                                         settings.get('disk_max', ''),
                                         width=6)
        self.fields['vcpu'] = IntegerField('vcpu',
                                           settings.get('vcpu', ''),
                                           settings.get('vcpu_min', ''),
                                           settings.get('vcpu_max', ''),
                                           width = 6)
        self.fields['hostname'] = StringField('hostname',
                                              settings.get('hostname', ''),
                                              width = 15)
        self.fields['ip_address'] = IpField('ip_address',
                                            settings.get('ip_address', ''),
                                            width = 16)
        self.fields['nameserver'] = IpField('nameserver',
                                            settings.get('nameserver', ''),
                                            width = 36)
        self.fields['passwd'] = PasswordField('passwd',
                                              settings.get('passwd', ''),
                                              width = 36)
        self.fields['passwd2'] = PasswordField('passwd2',
                                               settings.get('passwd', ''),
                                               width = 36)
        self.fields['startvm'] = CheckboxField('startvm',
                                               bool(settings.get('startvm', '')),
                                               display_name = 'Start VM')
        self.fields['onboot'] = CheckboxField('onboot',
                                              bool(settings.get('onboot', '')),
                                              display_name = 'Start on boot')
        self.labels['disk_max'] = str(settings.get('disk_max', ''))
        self.labels['disk_min'] = str(settings.get('disk_min', ''))
        self.labels['swap_max'] = str(settings.get('swap_max', ''))
        self.labels['swap_min'] = str(settings.get('swap_min', ''))
        self.labels['memory_max'] = str(settings.get('memory_max', ''))
        self.labels['memory_min'] = str(settings.get('memory_min', ''))
        self.labels['vcpu_min'] = str(settings.get('vcpu_min', ''))
        self.labels['vcpu_max'] = str(settings.get('vcpu_max', ''))
        Form.__init__(self, screen, title, self.fields)

    def display(self):
        self.gf = GridForm(self.screen, self.title, 1, 8)
        profile_items = [('Custom', 1)]
        storage_items = [('Local: /storage/local', 1),]
        cl = OneLineListbox('profile', profile_items, width=36)

        label1 = Label('* VM Resources')
        label1.setColors(colorsets['BORDER'])
        self.gf.add(label1, 0, 0, anchorLeft=1, padding=(0, 0, 0, 0))

        g2 = Grid(3, 2)
        g2.setField(self.fields['memory'], 0, 0)
        g2.setField(Label('VSwap (%s .. %s GB):' % (self.labels['swap_min'],
                                                    self.labels['swap_max'])),
                    1, 0, padding = (1, 0, 1, 0), anchorLeft=1)
        g2.setField(self.fields['swap'], 2, 0)
        g2.setField(self.fields['disk'], 0, 1)
        g2.setField(Label('CPUs (%s..%s):' % (self.labels['vcpu_min'],
                                              self.labels['vcpu_max'])),
                    1, 1, padding = (1, 0, 1, 0), anchorLeft=1)
        g2.setField(self.fields['vcpu'], 2, 1)

        g1 = VBox(4)
        g1.append(cl, growx=1)
        g1.append(g2)

        l2 = OneLineListbox('storage', storage_items, width=36)
        g1.append(l2)

        g4 = VBox(4)
        g4.append(Label('VM Profile'), anchorLeft=1, padding=(0, 0, 1, 0))
        memory_str = 'Memory (%s .. %s GB):' % (self.labels['memory_min'],
                                                self.labels['memory_max'])
        if len(memory_str) < 27:
            memory_str = memory_str.ljust(27, ' ')
        g4.append(Label(memory_str), anchorLeft=1, padding=(0, 0, 1, 0))
        g4.append(Label('Disk (%s..%sGB):' % (self.labels['disk_min'],
                                              self.labels['disk_max'])),
                  anchorLeft=1, padding=(0, 0, 1, 0))
        g4.append(Label('Sorage location:'), anchorLeft=1, padding=(0, 0, 1, 0))

        g3 = HBox(2)
        g3.append(g4)
        g3.append(g1)

        self.gf.add(g3, 0, 2)

        label2 = Label('* Network')
        label2.setColors(colorsets['BORDER'])
        self.gf.add(label2, 0, 3, anchorLeft=1)

        g5 = HBox(3)
        g5.append(self.fields['hostname'])
        g5.append(Label('IP:'), padding=(1, 0, 1, 0))
        g5.append(self.fields['ip_address'])

        g6 = VBox(2)
        g6.append(g5)
        g6.append(self.fields['nameserver'])
        g7 = VBox(2)
        g7.append(Label('Hostname:'), anchorLeft=1, growx=1)
        g7.append(Label('Nameservers:           '), anchorLeft=1, growx=1)

        g8 = HBox(2)
        g8.append(g7)
        g8.append(g6)

        self.gf.add(g8, 0, 4, anchorLeft=1, growx=1)

        label3 = Label('* Misc')
        label3.setColors(colorsets['BORDER'])
        self.gf.add(label3, 0, 5, anchorLeft=1)

        g9 = VBox(3)
        g9.append(self.fields['passwd'], anchorLeft=1)
        g9.append(self.fields['passwd2'], anchorLeft=1)
        g12 = HBox(2)
        g12.append(self.fields['startvm'], anchorLeft=1, padding=(0, 0, 3, 0))
        g12.append(self.fields['onboot'], anchorRight=1, padding=(4, 0, 0, 0))
        g9.append(g12)
        g10 = VBox(3)
        g10.append(Label('Root password'),  anchorLeft=1)
        g10.append(Label('Root password (x2)     '), anchorLeft=1)
        g11 = HBox(2)
        g11.append(g10)
        g11.append(g9)
        self.gf.add(g11, 0, 6, anchorLeft=1, growx=1)
        bb = ButtonBar(self.screen, (('Menu', 'menu', 'F12'), 'Create','Storage', 'Resources', 'Network'))
        self.gf.add(bb, 0, 7, padding=(0, 1, 0, 0))
        rv = self.gf.runOnce()
        return bb.buttonPressed(rv)

    def validate(self):
        Form.validate(self)
        if (self.fields['passwd'].validate() and self.fields['passwd2'].validate() and
                self.fields['passwd'].value() != self.fields['passwd2'].value()):
            self.errors.append(("passwd", "Passwords don't match."))
        return not self.errors


class EditVM(Form):
    def __init__(self, screen, title, settings):
        self.fields = {}
        self.labels = {}
        memory_max = min(sysres.get_ram_size_gb(),
                         float(settings.get("memory_max", 10 ** 30)))
        swap_max = min(sysres.get_swap_size_gb(),
                       float(settings.get("swap_max", 10 ** 30)))
        disk_max = min(sysres.get_disc_space_gb(),
                       float(settings.get("disk_max", 10 ** 30)))
        vcpu_max = min(sysres.get_cpu_count(),
                       int(settings.get("vcpu_max", 10 ** 10)))
        self.fields['memory'] = FloatField('memory',
                                           '%.6g' % float(settings['memory']),
                                           settings.get('memory_min', 0.1),
                                           settings.get('memory_max', memory_max),
                                           width=6)
        self.fields['swap'] = FloatField('swap',
                                         '%.6g' % float(settings['swap']),
                                         settings.get('swap_min', 0),
                                         settings.get('swap_max', swap_max),
                                         width=6)
        self.fields['diskspace'] = FloatField('diskspace',
                                              '%.6g' % float(settings['diskspace']['/']),
                                              settings.get('disk_min', 2.0),
                                              settings.get('disk_max', disk_max),
                                              width=6)
        self.fields['vcpu'] = IntegerField('vcpu',
                                           settings.get('vcpu', ''),
                                           settings.get('vcpu_min', 1),
                                           settings.get('vcpu_max', vcpu_max),
                                           width = 6)
        self.fields['name'] = StringField('name',
                                          settings.get('name', ''),
                                          width = 15)
        self.fields['ip_address'] = IpField('ip_address',
                                            settings['interfaces'][0]['ipaddr'],
                                            width = 16)
        self.fields['nameserver'] = IpField('nameserver',
                                            settings.get('nameserver', ''),
                                            width = 36)
        self.fields['onboot'] = CheckboxField('onboot',
                                              bool(settings.get('onboot', '')),
                                              display_name = 'Start on boot')
        self.labels['disk_max'] = str(settings.get('disk_max',
                                                   min(sysres.get_disc_space_gb(),
                                                       float(settings.get("disk_max", 10 ** 30)))))
        self.labels['disk_min'] = str(settings.get('disk_min', 2.0))
        self.labels['swap_max'] = str(settings.get('swap_max',
                                                   min(sysres.get_swap_size_gb(),
                                                       float(settings.get("swap_max", 10 ** 30)))))
        self.labels['swap_min'] = str(settings.get('swap_min', 0))
        self.labels['memory_max'] = str(settings.get('memory_min', 0.1))
        self.labels['memory_min'] = str(settings.get('memory_min',
                                                     min(sysres.get_ram_size_gb(),
                                                         float(settings.get("memory_max", 10 ** 30)))))
        self.labels['vcpu_min'] = str(settings.get('vcpu_min', 1))
        self.labels['vcpu_max'] = str(settings.get('vcpu_max',
                                                   min(sysres.get_cpu_count(),
                                                       int(settings.get("vcpu_max", 10 ** 10)))))
        Form.__init__(self, screen, title, self.fields)

    def display(self):
        self.gf = GridForm(self.screen, self.title, 1, 8)
        profile_items = [('Custom', 1)]
        storage_items = [('Local: /storage/local', 1),]
        cl = OneLineListbox('profile', profile_items, width=36)

        label1 = Label('* VM Resources')
        label1.setColors(colorsets['BORDER'])
        self.gf.add(label1, 0, 0, anchorLeft=1, padding=(0, 0, 0, 0))

        g2 = Grid(3, 2)
        g2.setField(self.fields['memory'], 0, 0)
        g2.setField(Label('VSwap (%s .. %s GB):' % (self.labels['swap_min'],
                                                    self.labels['swap_max'])),
                    1, 0, padding = (1, 0, 1, 0), anchorLeft=1)
        g2.setField(self.fields['swap'], 2, 0)
        g2.setField(self.fields['diskspace'], 0, 1)
        g2.setField(Label('CPUs (%s..%s):' % (self.labels['vcpu_min'],
                                              self.labels['vcpu_max'])),
                    1, 1, padding = (1, 0, 1, 0), anchorLeft=1)
        g2.setField(self.fields['vcpu'], 2, 1)

        g1 = VBox(4)
        g1.append(cl, growx=1)
        g1.append(g2)

        l2 = OneLineListbox('storage', storage_items, width=36)
        g1.append(l2)

        g4 = VBox(4)
        g4.append(Label('VM Profile'), anchorLeft=1, padding=(0, 0, 1, 0))
        memory_str = 'Memory (%s .. %s GB):' % (self.labels['memory_min'],
                                                self.labels['memory_max'])
        if len(memory_str) < 27:
            memory_str = memory_str.ljust(27, ' ')
        g4.append(Label(memory_str), anchorLeft=1, padding=(0, 0, 1, 0))
        g4.append(Label('Disk (%s..%sGB):' % (self.labels['disk_min'],
                                              self.labels['disk_max'])),
                  anchorLeft=1, padding=(0, 0, 1, 0))
        g4.append(Label('Sorage location:'), anchorLeft=1, padding=(0, 0, 1, 0))

        g3 = HBox(2)
        g3.append(g4)
        g3.append(g1)

        self.gf.add(g3, 0, 2)

        label2 = Label('* Network')
        label2.setColors(colorsets['BORDER'])
        self.gf.add(label2, 0, 3, anchorLeft=1)

        g5 = HBox(3)
        g5.append(self.fields['name'])
        g5.append(Label('IP:'), padding=(1, 0, 1, 0))
        g5.append(self.fields['ip_address'])

        g6 = VBox(2)
        g6.append(g5)
        g6.append(self.fields['nameserver'])
        g7 = VBox(2)
        g7.append(Label('Hostname:'), anchorLeft=1, growx=1)
        g7.append(Label('Nameservers:           '), anchorLeft=1, growx=1)

        g8 = HBox(2)
        g8.append(g7)
        g8.append(g6)

        self.gf.add(g8, 0, 4, anchorLeft=1, growx=1)

        label3 = Label('* Misc')
        label3.setColors(colorsets['BORDER'])
        self.gf.add(label3, 0, 5, anchorLeft=1)
        g9 = HBox(2)
        g9.append(Label('                       '))
        g10 = HBox(2)
        g10.append(self.fields['onboot'], anchorLeft=1, padding=(4, 0, 0, 0))
        g9.append(g10) 
        self.gf.add(g9, 0, 6, anchorLeft=1, growx=1)
        bb = ButtonBar(self.screen, (('Menu', 'menu', 'F12'), 'Commit','Storage', 'Resources', 'Network'))
        self.gf.add(bb, 0, 7, padding=(0, 1, 0, 0))
        rv = self.gf.runOnce()
        return bb.buttonPressed(rv)

    def validate(self):
        Form.validate(self)
        self.data['diskspace'] = {'/': float(self.fields['diskspace'].value()) }
        return not self.errors


class NetworkSettings(Form):
    def __init__(self, screen, title, settings):
        self.fields = {}
        self.labels = {}
        self.fields['hostname'] = StringField('hostname',
                                              settings.get('hostname', ''),
                                              width = 18)
        self.fields['ipv6'] = CheckboxField('ipv6',
                                            bool(settings.get('ipv6', False)),
                                            display_name = 'IPv6 Enabled')
        self.fields['nameserver'] = IpField('nameserver',
                                             settings.get('nameserver', ''), 
                                             width = 36)
        self.VIFS = Listbox(4, scroll=1)

        net_ifaces = []
        self.interfaces = settings.get('interfaces', [])
        if self.interfaces:
            for iface in self.interfaces:
                if iface.has_key('vlan'):
                    vlan = 'VLAN%-4s' % iface['vlan']
                else:
                    vlan = 'VLAN%-4s' % str(1)
                if iface.has_key('gw'):
                    gw = 'gw: %-15s' % iface['gw']
                else:
                    gw = ''
                net_ifaces.append(' '.join([vlan, '%-8s' % iface['name'],
                                            '%-15s' % iface.get('ipaddr',
                                                                iface.get('ipaddr', '')), gw]))
        for nr, iface in enumerate(net_ifaces):
            self.VIFS.insert(iface, nr, 0)

        self.labels['default_route'] = ''
        for iface in self.interfaces:
            if iface.has_key('default'):
                # TODO: if we have DHCP enabled iface then how to get that gw value
                if iface['default'] == 'yes' and iface['gw']:
                    self.labels['default_route'] = 'default via %s dev %s' % (iface['gw'],
                                                                              iface['ifname'])
        Form.__init__(self, screen, title, self.fields)
        self.settings = settings

    def display(self):
        self.gf = GridForm(self.screen, self.title, 1, 7)
        label1 = Label('* General')
        label1.setColors(colorsets['BORDER'])
        self.gf.add(label1, 0, 0, anchorLeft=1)

        g1 = HBox(2)
        g1.append(self.fields['hostname'])
        self.fields['ipv6'].setFlags(FLAG_DISABLED, 0)
        g1.append(self.fields['ipv6'], padding=(2, 0, 0, 0), anchorRight=1)

        g2 = VBox(2)
        g2.append(g1)
        g2.append(self.fields['nameserver'])

        g3 = VBox(2)
        g3.append(Label('Hostname:'), anchorLeft=1)
        g3.append(Label('Nameservers:'), anchorLeft=1, padding=(0, 0, 3, 0))

        g4 = HBox(2)
        g4.append(g3)
        g4.append(g2)

        self.gf.add(g4, 0, 1)

        label2 = Label('* Virtual Interfaces (VIF)')
        label2.setColors(colorsets['BORDER'])
        self.gf.add(label2, 0, 2, anchorLeft=True, padding=(0, 1, 0, 0))

        #('VLAN5123 venet1:0 10.10.1.10          gw: 10.10.1.254', 0, 0)
        #cbt.insert('VLAN5    eth0:0   192.168.123.321/24', 1, 0)
        #cbt.insert('VLAN7    eth1     10.30.5.75/24       gw: 10.30.5.254', 2, 0)

        self.gf.add(self.VIFS, 0, 3)

        label3 = Label('* Default Route')
        label3.setColors(colorsets['BORDER'])
        self.gf.add(label3, 0, 4, anchorLeft=True, padding=(0, 1, 0, 0))
        self.gf.add(Label(self.labels['default_route']), 0, 5, anchorLeft=True)

        bb = ButtonBar(self.screen, (('Back', 'back', 'F12'),('Save', ' ns_save'),
                                     ('Add VIF', 'addvif'), ('Edit VIF', 'editvif'),
                                     ('Set Default RT', 'route')))
        self.gf.add(bb, 0, 6, anchorLeft=True, padding=(0, 1, 0, 0))
        rv = self.gf.runOnce()
        return bb.buttonPressed(rv)

    def validate(self):
        Form.validate(self)
        try:
            self.settings['editvif'] = self.VIFS.current()
        except KeyError:
            self.settings['editvif'] = None
        return not self.errors


class AddVIF(Form):
    def __init__(self, screen, title, settings):
        self.fields = {}
        self.labels = {}
        Form.__init__(self, screen, title, self.fields)

    def display(self):
        self.gf = GridForm(self.screen, self.title, 1, 1)
        label = Label('* Choose VIF type')
        items = [('VENET (P-t-P IP)', 0),
                 ('VETH (ether IP)', 1),]
        listbox = Listbox(3, width=30, scroll=1)
        for (k, v) in items:
            listbox.append(k, v)
        bb = ButtonBar(self.screen, (('Cancel', 'back', 'F12'), ('Ok', 'add')))
        hbox = VBox(3)
        hbox.append(label, anchorLeft=1, padding=(0, 0, 0, 1))
        hbox.append(listbox)
        hbox.append(bb, padding=(0, 1, 0, 0))
        self.gf.add(hbox, 0, 0)
        rv = self.gf.runOnce()
        if bb.buttonPressed(rv) == 'back':
            return 'network'
        logic = {0: 'venet', 1: 'veth', 2: 'veth_alias'}
        return logic[listbox.current()]


class EditVIF(Form):
    def __init__(self, screen, title, settings):
        self.fields = {}
        self.labels = {}
        self.settings = settings
        self.interface = self.settings['interfaces'][settings['editvif']]
        self.fields['managed'] = CheckboxField('managed',
                                               bool(self.interface.get('managed', True)),
                                               display_name = 'Managed')
        self.fields['dhcp'] = CheckboxField('dhcp', bool(self.interface.get('dhcp', False)),
                                            display_name = 'DHCP')
        self.fields['vif_mac'] = StringField('vif_mac',
                                             self.interface.get('vif_mac', '(autogenerated)'),
                                             required = False,
                                             width = 18)
        self.fields['mac'] = StringField('mac',
                                         self.interface.get('mac', '(autogenerated)'),
                                         required = False,
                                         width = 18)
        self.fields['ipaddr'] = IpField('ipaddr',
                                        self.interface.get('ipaddr', ''),
                                        width = 16)
        self.fields['mask'] = IpField('mask',
                                      self.interface.get('mask', ''),
                                      required = False,
                                      width=16)
        self.fields['gw'] = IpField('gw',
                                    self.interface.get('gw', ''),
                                    required = False,
                                    width = 16)
        # TODO: add vlan id and bw controls
        self.labels['name'] = self.interface.get('name', '')
        self.labels['host_bridge'] = self.interface.get('host_ifname', '')
        Form.__init__(self, screen, title, self.fields)

    def display(self):
        self.gf = GridForm(self.screen, self.title, 1, 5)

        label1 = Label('* VIF Settings')
        label1.setColors(colorsets['BORDER'])
        self.gf.add(label1, 0, 0, anchorLeft=1)

        hbrr = VBox(4)
        man_dhcp = HBox(2)
        man_dhcp.append(self.fields['managed'], anchorLeft=1, padding=(0, 0, 2, 0))
        man_dhcp.append(self.fields['dhcp'], anchorRight=1, padding=(2, 0, 0, 0))
        hbrr.append(man_dhcp)
        hbrr.append(Label('Host bridge: %s' % self.labels['host_bridge']), anchorLeft=1)
        vif_mac_entry=self.fields['vif_mac']
        vif_mac_entry.setFlags(FLAG_DISABLED, 0)
        hbrr.append(vif_mac_entry)
        hbrr.append(self.fields['mac'])
        hbrl = VBox(4)
        hbrl.append(Label(''))
        hbrl.append(Label(''))
        hbrl.append(Label('VIF MAC:'), anchorRight=1, padding=(2, 0, 1, 0))
        hbrl.append(Label('Host MAC:'), anchorRight=1, padding=(2, 0, 1, 0))
        hbll = VBox(3)
        hbll.append(Label('IP Addr:'), anchorLeft=1, padding=(0, 0, 1, 0))
        hbll.append(Label('Netbask:'), anchorLeft=1, padding=(0, 0, 1, 0))
        hbll.append(Label('Gateway:'), anchorLeft=1, padding=(0, 0, 1, 0))
        hblr = VBox(3)
        hblr.append(self.fields['ipaddr'])
        hblr.append(self.fields['mask'])
        hblr.append(self.fields['gw'])
        vbl = HBox(2)
        vbl.append(hbll)
        vbl.append(hblr)
        hbl = VBox(2)
        hbl.append(Label('Device name: %s' % self.labels['name']), anchorLeft=1)
        hbl.append(vbl)
        vb = HBox(3)
        vb.append(hbl)
        vb.append(hbrl)
        vb.append(hbrr)
        self.gf.add(vb, 0, 1)
        label2 = Label('* VIF Rules')
        label2.setColors(colorsets['BORDER'])
        self.gf.add(label2, 0, 2, anchorLeft=1, padding=(0, 1, 0, 0))
        vb = HBox(6)
        vb.append(Label('VLAN ID:'), padding=(0, 0, 1, 0))
        vb.append(Entry(5, '15'), padding=(0, 0, 2, 0))
        vb.append(Label('BW Limit (Mbps):'), padding=(0, 0, 1, 0))
        vb.append(Entry(7, '10'), padding=(0, 0, 2, 0))
        vb.append(Label('BW Burst (kb):'), padding=(0, 0, 1, 0))
        vb.append(Entry(5, '1'))
        self.gf.add(vb, 0, 3)
        bb = ButtonBar(self.screen, (('Cancel', 'back', 'F12'), ('Ok', 'network')))
        self.gf.add(bb, 0, 4, padding=(0, 2, 0, 0))
        rv = self.gf.runOnce()
        return bb.buttonPressed(rv)

    def validate(self):
        Form.validate(self)
        with open('/root/dhcp.txt', 'wt') as f:
            from pprint import pformat
            f.write(pformat(self.data))
        if self.data['dhcp']:
            iface = {'name': self.interface['name'],
                     'managed': self.data['managed'],
                     'dhcp': 'Yes'}
            self.settings['interfaces']['editvif'] = iface
        else:
            del (self.data['vif_mac'])
        self.settings['interfaces']['editvif'] = self.data
        return not self.errors


class VenetSettings(Form):
    def __init__(self, screen, title, settings):
        self.fields = {}
        self.labels = {}
        self.fields['ipaddr'] = IpField('ipaddr',
                                        '', width = 16)
        Form.__init__(self, screen, title, self.fields)
        self.settings = settings

    def display(self):
        self.gf = GridForm(self.screen, self.title, 1, 4)
        label = Label('* VIF Settings')
        label.setColors(colorsets['BORDER'])
        self.gf.add(label, 0, 0, anchorLeft=1, padding=(0, 0, 0, 1))
        self.gf.add(Label('Device name: venet0:x'), 0, 1, anchorLeft=1)
        vbox = HBox(2)
        vbox.append(Label('IP Addr:'), padding=(0, 0, 2, 0))
        vbox.append(self.fields['ipaddr'])
        self.gf.add(vbox, 0, 2, anchorLeft=1)
        bb = ButtonBar(self.screen, (('Cancel', 'back', 'F12'), ('Ok', 'network')))
        self.gf.add(bb, 0, 3, padding=(0, 2, 0, 0))
        self.rv = self.gf.runOnce()
        return bb.buttonPressed(self.rv)

    def validate(self):
        Form.validate(self)
        if not self.settings.get('num_venet', ''):
            self.settings['num_venet'] = 0
        new_venet = {'ipaddr': self.fields['ipaddr'].value(), 'mac': '00:00:00:00:00:00',
                     'type': 'ethernet', 'name': 'venet0:%s' % (self.settings['num_venet'])}
        self.data['interfaces'] = new_venet
        self.settings['num_venet'] += 1
        return not self.errors


class Resources(Form):
    # TODO: add support for VCPU masks, UBC limits
    def __init__(self, screen, title, settings):
        self.fields = {}
        self.labels = {}
        self.fields['vcpu'] = IntegerField('vcpu',
                                           settings.get('vcpu', ''),
                                           settings.get('vcpu_min', 1),
                                           settings.get('vcpu_max',
                                                        min(sysres.get_cpu_count(),
                                                            int(settings.get("vcpu_max", 10 ** 10)))),
                                           width = 4)
        self.fields['vcpulimit'] = IntegerField('vcpulimit',
                                                settings['vcpulimit'],
                                                50, 100,
                                                width = 4)
        ioprio_values = [('Low', 0),
                         ('Default', 4),
                         ('High', 7)]
        self.fields['ioprio'] = OneLineListbox('ioprio', ioprio_values, 25, settings.get('ioprio', None))
        self.fields['onboot'] = CheckboxField('onboot',
                                              bool(settings.get('onboot', '')),
                                              display_name = 'Start on boot')
        self.fields['bootorder'] = IntegerField('bootorder',
                                                settings.get('bootorder', ''),
                                                required = False, width = 4)
        self.labels['vcpu_min'] = str(settings.get('vcpu_min', 1))
        self.labels['vcpu_max'] = str(settings.get('vcpu_max', ''))
        Form.__init__(self, screen, title, self.fields)

    def display(self):
        self.gf = GridForm(self.screen, self.title, 1, 7)
        label1 = Label('* CPU limits')
        label1.setColors(colorsets['BORDER'])
        label2 = Label('* Primary UBC limits')
        label2.setColors(colorsets['BORDER'])
        label3 = Label('* VM boot params')
        label3.setColors(colorsets['BORDER'])
        self.gf.add(label1, 0, 0, anchorLeft=1)
        self.gf.add(label2, 0, 2, anchorLeft=1, padding=(0, 0, 0, 0))
        self.gf.add(label3, 0, 4, anchorLeft=1, padding=(0, 0, 0, 0))
        hbll = VBox(2)
        hbll.append(Label('CPUs (%s..%s):' % (self.labels['vcpu_min'],
                                              self.labels['vcpu_max'])), anchorLeft=1)
        hbll.append(Label('CPU usage limit (%):'), anchorLeft=1)
        hblr = VBox(2)
        hblr.append(self.fields['vcpu'])
        hblr.append(self.fields['vcpulimit'])
        hbrl = VBox(2)
        hbrl.append(Label('CPU Priority:'), anchorRight=1)
        hbrl.append(Label('CPU mask (1..%s):' % self.labels['vcpu_max']),
                    anchorRight=1)
        hbrr = VBox(2)
        hbrr.append(self.fields['ioprio'])
        masks = Entry(14, '')
        masks.setFlags(FLAG_DISABLED, 0)
        hbrr.append(masks)
        vb_cpu = HBox(4)
        vb_cpu.append(hbll, padding=(0, 0, 1, 0))
        vb_cpu.append(hblr, padding=(0, 0, 1, 0))
        vb_cpu.append(hbrl, padding=(0, 0, 1, 0))
        vb_cpu.append(hbrr)
        self.gf.add(vb_cpu, 0, 1)

        hbll = VBox(5)
        hbll.append(Label('Parameter'), anchorLeft=1)
        hbll.append(Label('NUMPROC:'), anchorLeft=1)
        hbll.append(Label('NUMTCPSOCK:'), anchorLeft=1)
        hbll.append(Label('NUMOTEHRSOCK:'), anchorLeft=1)
        hbll.append(Label('VMGUARPAGES:'), anchorLeft=1)
        hblr = VBox(5)
        hblr.append(Label('Barrier'), anchorLeft=1)
        hblr.append(Entry(12, 'UNLIMITED'))
        hblr.append(Entry(12, 'UNLIMITED'))
        hblr.append(Entry(12, 'UNLIMITED'))
        hblr.append(Entry(12, 'UNLIMITED'))
        hbrl = VBox(5)
        hbrl.append(Label('Limit'), anchorLeft=1)
        hbrl.append(Entry(12, 'UNLIMITED'))
        hbrl.append(Entry(12, 'UNLIMITED'))
        hbrl.append(Entry(12, 'UNLIMITED'))
        hbrl.append(Entry(12, 'UNLIMITED'))
        hbrr = VBox(5)
        labelf = Label('Failcnt')
        labelf.setColors(colorsets['BUTTON'])
        hbrr.append(labelf)
        entry1 = Entry(8, '0')
        entry1.setFlags(FLAG_DISABLED, 0)
        entry2 = Entry(8, '0')
        entry2.setFlags(FLAG_DISABLED, 0)
        entry3 = Entry(8, '0')
        entry3.setFlags(FLAG_DISABLED, 0)
        entry4 = Entry(8, '0')
        entry4.setFlags(FLAG_DISABLED, 0)
        hbrr.append(entry1)
        hbrr.append(entry2)
        hbrr.append(entry3)
        hbrr.append(entry4)
        vb_ubc = HBox(4)
        vb_ubc.append(hbll, padding=(0, 0, 4, 0))
        vb_ubc.append(hblr, padding=(0, 0, 2, 0))
        vb_ubc.append(hbrl, padding=(0, 0, 2, 0))
        vb_ubc.append(hbrr, padding=(0, 0, 2, 0))
        self.gf.add(vb_ubc, 0, 3)

        vb_boot = HBox(4)
        vb_boot.append(Label(' '*8), padding=(0, 0, 2, 0))
        vb_boot.append(self.fields['onboot'], padding=(0, 0, 2, 0))
        vb_boot.append(Label('Boot order (1..999)'), padding=(0, 0, 2, 0))
        vb_boot.append(self.fields['bootorder'])
        self.gf.add(vb_boot, 0, 5)

        bb = ButtonBar(self.screen, (('Cancel', 'back', 'F12'), 'Save'))
        self.gf.add(bb, 0, 6, padding=(0, 1, 0, 0))
        rv = self.gf.runOnce()
        return bb.buttonPressed(rv)


class Storage(Form):
    def __init__(self, screen, title, settings):
        self.fields = {}
        self.labels = {}
        self.fields['bind_mounts'] = BindMountsField('bind_mounts',
                                                     settings.get('bind_mounts', ''),
                                                     required = False,
                                                     width = 25)
        ioprio_values = [('Low', 0),
                         ('Default', 4),
                         ('High', 7)]
        self.fields['ioprio'] = OneLineListbox('ioprio', ioprio_values, 25, settings.get('ioprio', None))
        Form.__init__(self, screen, title, self.fields)

    def display(self):
        self.gf = GridForm(self.screen, self.title, 1, 6)
        label1 = Label('Bind mounts')
        label1.setColors(colorsets['BORDER'])
        label2 = Label('IO Priority')
        label2.setColors(colorsets['BORDER'])
        self.gf.add(label1, 0, 0, anchorLeft=1)
        self.gf.add(self.fields['bind_mounts'], 0, 1, anchorLeft=1, padding=(0, 0, 0, 0))
        self.gf.add(Label('/src1,/dest1;/srcN,/destN'), 0, 2, anchorLeft=1)
        self.gf.add(label2, 0, 3, anchorLeft=1, padding=(0, 1, 0, 0))
        self.gf.add(self.fields['ioprio'], 0, 4, anchorLeft=1, padding=(0, 0, 0, 0))
        bb = ButtonBar(self.screen, (('Cancel', 'back', 'F12'), 'Ok'))
        self.gf.add(bb, 0, 5, padding=(0, 1, 0, 0))
        rv = self.gf.runOnce()
        return bb.buttonPressed(rv)


class KvmForm(Form):

    def __init__(self, screen, title, settings):
        self.memory = FloatField("memory", settings["memory"], settings["memory_min"], settings["memory_max"])
        self.vcpu = IntegerField("vcpu", settings["vcpu"], settings["vcpu_min"], settings["vcpu_max"])
        self.hostname = StringField("hostname", settings.get("hostname", ""))
        Form.__init__(self, screen, title, [self.memory, self.vcpu, self.hostname])

    def display(self):
        button_save, button_exit = Button("Create VM"), Button("Main menu")
        separator = (Textbox(20, 1, "", 0, 0), Textbox(20, 1, "", 0, 0))
        rows = [
            (Textbox(20, 1, "Memory size (GB):", 0, 0), self.memory),
            (Textbox(20, 1, "Memory min/max:", 0, 0),
             Textbox(20, 1, "%s / %s" % (self.memory.min_value, self.memory.max_value), 0, 0)),
            separator,
            (Textbox(20, 1, "Number of CPUs:", 0, 0), self.vcpu),
            (Textbox(20, 1, "CPU number min/max:", 0, 0),
             Textbox(20, 1, "%s / %s" % (self.vcpu.min_value, self.vcpu.max_value), 0, 0)),
            separator,
            (Textbox(20, 1, "Hostname:", 0, 0), self.hostname),
            separator,
            (button_save, button_exit)
        ]
        form = GridForm(self.screen, self.title, 2, len(rows))
        for i, row in enumerate(rows):
            for j, cell in enumerate(row):
                form.add(cell, j, i)
        return form.runOnce() != button_exit


class OpenvzForm(Form):

    def __init__(self, screen, title, settings):
        self.memory = FloatField("memory", settings["memory"], settings["memory_min"], settings["memory_max"])
        self.swap = FloatField("swap", settings["swap"], settings["swap_min"], settings["swap_max"])
        self.vcpu = FloatField("vcpu", settings["vcpu"], settings["vcpu_min"], settings["vcpu_max"])
        self.vcpulimit = IntegerField("vcpulimit", settings["vcpulimit"], settings["vcpulimit_min"], settings["vcpulimit_max"])
        self.disk = FloatField("disk", settings["disk"], settings["disk_min"], settings["disk_max"])
        self.ioprio = RadioBarField("ioprio", screen, [('Low    ', 0, settings["ioprio"] == 0),
                                                       ('Default', 4, settings["ioprio"] == 4),
                                                       ('High   ', 7, settings["ioprio"] == 7)])
        self.bind_mounts = BindMountsField("bind_mounts", settings["bind_mounts"], required=False)
        self.hostname = StringField("hostname", settings.get("hostname", ""))
        self.ip_address = IpField("ip_address", settings["ip_address"], display_name="IP address")
        self.nameserver = IpField("nameserver", settings["nameserver"])
        self.password = PasswordField("passwd", settings["passwd"], display_name="password")
        self.password2 = PasswordField("passw2", settings["passwd"], display_name="password")
        self.ostemplate = StringField("ostemplate", settings["ostemplate"], display_name="OS template")
        self.startvm = CheckboxField("startvm", settings.get("startvm", 0), display_name="Start VM")
        self.onboot = CheckboxField("onboot", settings.get("onboot", 0), display_name="Start on boot")
        Form.__init__(self, screen, title, [self.memory, self.swap, self.vcpu,
                                            self.vcpulimit, self.disk, self.ioprio,
                                            self.bind_mounts, self.hostname,
                                            self.ip_address, self.nameserver,
                                            self.password, self.password2,
                                            self.ostemplate, self.startvm,
                                            self.onboot])
        self.settings = settings  # save passed parameters for convenience

    def display(self):
        button_exit, button_save = Button("Back"), Button("Create VM")
        separator = (Textbox(20, 1, "", 0, 0), Textbox(20, 1, "", 0, 0))
        rows = [
            (Textbox(20, 1, "Memory size (GB):", 0, 0), self.memory),
            (Textbox(20, 1, "Memory min/max:", 0, 0),
             Textbox(20, 1, "%s / %s" % (self.memory.min_value, self.memory.max_value), 0, 0)),
            (Textbox(20, 1, "VSwap size (GB):", 0, 0), self.swap),
            (Textbox(20, 1, "VSwap min/max:", 0, 0),
             Textbox(20, 1, "%s / %s" % (self.swap.min_value, self.swap.max_value), 0, 0)),
            (Textbox(20, 1, "Number of CPUs:", 0, 0), self.vcpu),
            (Textbox(20, 1, "CPU number min/max:", 0, 0),
             Textbox(20, 1, "%s / %s" % (self.vcpu.min_value, self.vcpu.max_value), 0, 0)),
            (Textbox(20, 1, "CPU usage limit (%):", 0, 0), self.vcpulimit),
            (Textbox(20, 1, "CPU usage min/max:", 0, 0),
             Textbox(20, 1, "%s / %s" % (self.vcpulimit.min_value, self.vcpulimit.max_value), 0, 0)),
            (Textbox(20, 1, "Disk size (GB):", 0, 0), self.disk),
            (Textbox(20, 1, "Disk size min/max:", 0, 0),
             Textbox(20, 1, "%s / %s" % (self.disk.min_value, self.disk.max_value), 0, 0)),
            (Textbox(20, 1, "IO Priority:", 0, 0), self.ioprio),
            (Textbox(20, 1, "Bind mounts:", 0, 0), self.bind_mounts),
            (Textbox(20, 1, "", 0, 0),
             Textbox(20, 1, "/src1,/dst1;/srcN,..", 0, 0)),
            (Textbox(20, 1, "Hostname:", 0, 0), self.hostname),
            (Textbox(20, 1, "IP-address:", 0, 0), self.ip_address),
            (Textbox(20, 2, "Nameserver:", 0, 0), self.nameserver),
            (Textbox(20, 1, "Root password:", 0, 0), self.password),
            (Textbox(20, 2, "Root password x2:", 0, 0), self.password2),
            (Textbox(20, 2, "OS Template:", 0, 0), self.ostemplate),
            (self.startvm, self.onboot),
            separator,
            (button_save, button_exit)
        ]
        form = GridForm(self.screen, self.title, 2, len(rows))
        for i, row in enumerate(rows):
            for j, cell in enumerate(row):
                form.add(cell, j, i)
        return form.runOnce() != button_exit

    def validate(self):
        Form.validate(self)
        if (self.password.validate() and self.password2.validate() and
                self.password.value() != self.password2.value()):
            self.errors.append(("passwd", "Passwords don't match."))
        bm_valid = self.bind_mounts.validate()
        if bm_valid:
            error_str = "\n".join([s[1] for s in bm_valid])
            self.errors.append(("bind_mounts", "%s" % error_str))
        return not self.errors


class OpenvzTemplateForm(Form):

    def __init__(self, screen, title, settings):
        self.memory = FloatField("memory", settings["memory"])
        self.memory_min = FloatField("memory_min", settings.get("memory_min", ""), display_name="min memory", required=False)
        self.memory_max = FloatField("memory_max", settings.get("memory_max", ""), display_name="max memory", required=False)
        self.vcpu = FloatField("vcpu", settings["vcpu"])
        self.vcpu_min = FloatField("vcpu_min", settings.get("vcpu_min", ""), display_name="min vcpu", required=False)
        self.vcpu_max = FloatField("vcpu_max", settings.get("vcpu_max", ""), display_name="max vcpu", required=False)
        self.disk = FloatField("disk", settings["disk"])
        self.ostemplate = StringField("ostemplate", settings.get("ostemplate", ""))
        Form.__init__(self, screen, title, [self.memory, self.memory_min,
                                            self.memory_max, self.vcpu,
                                            self.vcpu_min, self.vcpu_max,
                                            self.disk, self.ostemplate])

    def display(self):
        button_save, button_exit = Button("Create VM"), Button("Back")
        separator = (Textbox(20, 1, "", 0, 0), Textbox(20, 1, "", 0, 0))
        rows = [
            (Textbox(20, 1, "Memory size (GB):", 0, 0), self.memory),
            (Textbox(20, 1, "Min memory size (GB):", 0, 0), self.memory_min),
            (Textbox(20, 1, "Max memory size (GB):", 0, 0), self.memory_max),
            separator,
            (Textbox(20, 1, "Number of CPUs:", 0, 0), self.vcpu),
            (Textbox(20, 1, "Min number of CPUs:", 0, 0), self.vcpu_min),
            (Textbox(20, 1, "Max number of CPUs:", 0, 0), self.vcpu_max),
            separator,
            (Textbox(20, 1, "Disk size (GB):", 0, 0), self.disk),
            separator,
            (Textbox(20, 1, "OS template:", 0, 0), self.ostemplate),
            separator,
            (button_exit, button_save)
        ]
        form = GridForm(self.screen, self.title, 2, len(rows))
        for i, row in enumerate(rows):
            for j, cell in enumerate(row):
                form.add(cell, j, i)
        return form.runOnce() != button_exit

    def validate(self):
        if Form.validate(self):
            self.errors.extend(validate_range("memory", self.memory.value(),
                                              self.memory_min.value(),
                                              self.memory_max.value(), float))
            self.errors.extend(validate_range("vcpu", self.vcpu.value(),
                                              self.vcpu_min.value(),
                                              self.vcpu_max.value(), int))
        return not self.errors


class KvmTemplateForm(Form):

    def __init__(self, screen, title, settings):
        self.memory = FloatField("memory", settings["memory"])
        self.memory_min = FloatField("memory_min", settings.get("memory_min", ""), display_name="min memory", required=False)
        self.memory_max = FloatField("memory_max", settings.get("memory_max", ""), display_name="max memory", required=False)
        self.vcpu = FloatField("vcpu", settings["vcpu"])
        self.vcpu_min = FloatField("vcpu_min", settings.get("vcpu_min", ""), display_name="min vcpu", required=False)
        self.vcpu_max = FloatField("vcpu_max", settings.get("vcpu_max", ""), display_name="max vcpu", required=False)
        Form.__init__(self, screen, title, [self.memory, self.memory_min, self.memory_max,
                                            self.vcpu, self.vcpu_min, self.vcpu_max])

    def display(self):
        button_save, button_exit = Button("Create"), Button("Back")
        separator = (Textbox(20, 1, "", 0, 0), Textbox(20, 1, "", 0, 0))
        rows = [
            (Textbox(20, 1, "Memory size (GB):", 0, 0), self.memory),
            (Textbox(20, 1, "Min memory size (GB):", 0, 0), self.memory_min),
            (Textbox(20, 1, "Max memory size (GB):", 0, 0), self.memory_max),
            separator,
            (Textbox(20, 1, "Number of CPUs:", 0, 0), self.vcpu),
            (Textbox(20, 1, "Min number of CPUs:", 0, 0), self.vcpu_min),
            (Textbox(20, 1, "Max number of CPUs:", 0, 0), self.vcpu_max),
            separator,
            (button_exit, button_save)
        ]
        form = GridForm(self.screen, self.title, 2, len(rows))
        for i, row in enumerate(rows):
            for j, cell in enumerate(row):
                form.add(cell, j, i)
        return form.runOnce() != button_exit

    def validate(self):
        if Form.validate(self):
            if (self.memory_min.value() and self.memory_max.value() and
                    float(self.memory_min.value()) > float(self.memory_max.value())):
                self.errors.extend([("memory", "Min memory exceeds max memory value.")])
            else:
                self.errors.extend(validate_range("memory", self.memory.value(),
                                                  self.memory_min.value(),
                                                  self.memory_max.value(), float))
                self.errors.extend(validate_range("vcpu", self.vcpu.value(),
                                                  self.vcpu_min.value(),
                                                  self.vcpu_max.value(), int))
        return not self.errors


class OpenvzModificationForm(Form):

    def __init__(self, screen, title, settings):
        self.settings = settings
        self.memory = FloatField("memory", float(settings["memory"]) / 1024)
        self.swap = FloatField("swap", float(settings["swap"]) / 1024)
        self.vcpu = IntegerField("vcpu", settings["vcpu"])
        self.bootorder = IntegerField("bootorder", settings.get("bootorder"), required=False)
        self.disk = FloatField("diskspace", float(settings["diskspace"]["/"]) / 1024)
        self.ioprio = RadioBarField("ioprio", screen, [('Low    ', 0, settings["ioprio"] == 0),
                                                       ('Default', 4, settings["ioprio"] == 4),
                                                       ('High   ', 7, settings["ioprio"] == 7)])
        self.bind_mounts = BindMountsField("bind_mounts", settings["bind_mounts"], required=False)
        self.vcpulimit = IntegerField("vcpulimit", settings["vcpulimit"], min_value=0)
        self.onboot = CheckboxField("onboot", settings.get("onboot", 0), display_name="Start on boot")
        Form.__init__(self, screen, title, [self.memory, self.vcpu, self.disk, self.ioprio,
                                            self.bind_mounts, self.swap, self.onboot, self.bootorder,
                                            self.vcpulimit])

    def display(self):
        button_save, button_exit = Button("Update"), Button("Back")
        separator = (Textbox(20, 1, "", 0, 0), Textbox(20, 1, "", 0, 0))
        rows = [
            (Textbox(20, 1, "Memory size (GB):", 0, 0), self.memory),
            separator,
            (Textbox(20, 1, "Swap size (GB):", 0, 0), self.swap),
            separator,
            (Textbox(20, 1, "Nr. of CPUs:", 0, 0), self.vcpu),
            separator,
            (Textbox(20, 1, "CPU usage limit (%):", 0, 0), self.vcpulimit),
            separator,
            (Textbox(20, 1, "Disk size (GB):", 0, 0), self.disk),
            separator,
            (Textbox(20, 1, "IO Priority:", 0, 0), self.ioprio),
            separator,
            (Textbox(20, 1, "Bind mounts:", 0, 0), self.bind_mounts),
            (Textbox(20, 1, "", 0, 0),
             Textbox(20, 1, "/src1,/dst1;/srcN,..", 0, 0)),
            separator,
            (Textbox(20, 1, "", 0, 0), self.onboot),
            separator,
            (Textbox(20, 1, "Boot order:", 0, 0), self.bootorder),
            separator,
            (button_exit, button_save)
        ]
        form = GridForm(self.screen, self.title, 2, len(rows))
        for i, row in enumerate(rows):
            for j, cell in enumerate(row):
                form.add(cell, j, i)
        return form.runOnce() != button_exit

    def validate(self):
        if Form.validate(self):
            # TODO disallow decrease of disk size, which would break OS
            pass
        bm_valid = self.bind_mounts.validate()
        if bm_valid:
            error_str = "\n".join([s[1] for s in bm_valid])
            self.errors.append(("bind_mounts", "%s" % error_str))
        if self.memory.value() < self.settings["memory_min"]:
            err_msg = "Memory size can not be lower than minimum defined in template: %s GB" % self.settings["memory_min"]
            self.errors.append(("memory", err_msg))
        return not self.errors


class OpenVZMigrationForm(Form):

    def __init__(self, screen, title):
        self.target = HostnameField("target host", '')
        self.live = CheckboxField("live", default=0, display_name='(risky)')
        Form.__init__(self, screen, title, [self.target, self.live])

    def display(self):
        button_save, button_exit = Button("Migrate"), Button("Back")
        separator = (Textbox(20, 1, "", 0, 0), Textbox(20, 1, "", 0, 0))
        rows = [
            (Textbox(20, 1, "Hostname/IP:", 0, 0), self.target),
            separator,
            (Textbox(20, 1, "Live migration:", 0, 0), self.live),
            separator,
            (button_save, button_exit)
        ]
        form = GridForm(self.screen, self.title, 2, len(rows))
        for i, row in enumerate(rows):
            for j, cell in enumerate(row):
                form.add(cell, j, i)
        return form.runOnce() != button_exit

    def validate(self):
        if Form.validate(self):
            pass
        return not self.errors


# ------------- Field widgets --------------

class CheckboxField(Checkbox):

    def __init__(self, name, default, display_name=None):
        self.name = name
        self.display_name = display_name or name
        Checkbox.__init__(self, "%s" % self.display_name, int(default))

    def validate(self):
        return True


class Field(Entry):
    errors = []

    def __init__(self, name, default, width, min_value=None, max_value=None,
                 expected_type=None, password=0, display_name=None, required=True):
        Entry.__init__(self, width, "%s" % default, password=password)
        self.name, self.min_value, self.max_value = name, min_value, max_value
        self.expected_type, self.required = expected_type, required
        self.display_name = display_name or name

    def validate(self):
        self.errors = []
        if self.required:
            er = validate_required(self.display_name, self.value())
            if er:
                self.errors.extend(er)
                return False
        if self.expected_type and self.value():
            er = validate_type(self.display_name, self.value(), self.expected_type)
            if er:
                self.errors.extend(er)
                return False
            if self.min_value or self.max_value:
                er = validate_range(self.display_name, self.value(), self.min_value,
                                    self.max_value, self.expected_type)
                if er:
                    self.errors.extend(er)
                    return False
        return not self.errors


class StringField(Field):
    def __init__(self, name, default, required=True, width=20, display_name=None):
        Field.__init__(self, name, default, width, display_name=display_name, required=required)

    def validate(self):
        if Field.validate(self):
            if re.search(r"\s", self.value()):
                self.errors = [(self.name, "%s should not include white spaces. Got: '%s'"
                                            % (self.name.capitalize(), self.value()))]


class BindMountsField(Field):
    def __init__(self, name, default, required=True, width=20, display_name=None):
        Field.__init__(self, name, default, required=required, width=width, display_name=display_name)

    def validate(self):
        # Input should be in the form of '/src,/dst(;/src,/dst)'
        if Field.validate(self) and self.value():
            # TODO: handle \;
            # TODO: handle comma as it can be valid path
            bm = self.value().strip().split(';')
            for pair in bm:
                if len(pair) == 0:
                    continue
                items = pair.split(',')
                if len(items) < 2:
                    self.errors.append((self.name, "Bind mounts syntax is /src1,/dst1;/srcN,/dstN"))
                    continue
                if  not items[0].startswith('/') and not os.path.isdir(items[0]):
                    self.errors.append((self.name,
                                        "'%s' is not a valid path on base system."
                                        % (items[0])))
                if not items[1].startswith('/'):
                    self.errors.append((self.name,
                                        "'%s' is not a valid path."
                                        % (items[0])))
        return self.errors


class RadioBarField(RadioBar):
    """ RadioBarField extends RadioBar to add value and validate methods
    and bring it to line with other field classes"""
    def __init__(self, name, screen, fields):
        RadioBar.__init__(self, screen, fields)
        self.name = name

    def value(self):
        return self.getSelection()

    def validate(self):
        return True


class IpField(Field):
    def __init__(self, name, default, required=True, width=20, display_name=None):
        Field.__init__(self, name, default, width, display_name=display_name, required=required)

    def validate(self):
        if Field.validate(self):
            try:
                socket.inet_aton(self.value())
            except socket.error:
                self.errors = [(self.name, "%s format is not correct. Got: '%s'"
                                            % (self.name.capitalize(), self.value()))]
                return False
        return True


class HostnameField(Field):
    def __init__(self, name, default, required=True, width=20, display_name=None, port=22):
        Field.__init__(self, name, default, width, display_name=display_name, required=required)
        self.port = port

    def validate(self):
        if Field.validate(self):
            try:
                socket.getaddrinfo(self.value(), self.port)
            except socket.error:
                self.errors = [(self.name, "%s %s:%s' is unreachable.'"
                                            % (self.name.capitalize(), self.value(), self.port))]
                return False
        return True


class PasswordField(Field):
    def __init__(self, name, default, required=True, width=20, display_name=None):
        Field.__init__(self, name, default, width, required=required,
                       password=1, display_name=display_name)

    def validate(self):
        # TODO: cracklib?
        return Field.validate(self)


class IntegerField(Field):
    def __init__(self, name, default, min_value=None, max_value=None,
                 width=20, display_name=None, required=True):
        Field.__init__(self, name, default, width, min_value=min_value,
                       max_value=max_value, expected_type=int, display_name=display_name,
                       required=required)


class FloatField(Field):
    def __init__(self, name, default, min_value=None, max_value=None,
                 width=20, display_name=None, required=True):
        Field.__init__(self, name, default, width, min_value=min_value,
                       max_value=max_value, expected_type=float, display_name=display_name,
                       required=required)


class OneLineListbox(Listbox):
    """ Helper for one line Listbox.
    This one adds visual aids ('<' '>') and truncates string if need be."""
    def __init__(self, name, items=[], width=24, current = None):
        self.list_items = []
        self.name = name
        self.active = items[0][1]
        Listbox.__init__(self, 1, width=width, oneline=True)
        for (k, v) in items:
            spaces = width - len(k) - 3
            if spaces < 0:
                nv = '< ' + k[:(width - 3)] + '>'
            nv = '< ' + k + ' '*spaces + '>'
            self.list_items.append((nv, v))
        for (k, v) in self.list_items:
            self.append(k, v)
        if current:
            self.setCurrent(current)
            self.active = current

    def validate(self):
        return True

    def value(self):
        return self.current()


def validate_required(name, value):
    return [] if value else [(name, "%s is required." % name.capitalize())]


def validate_type(name, value, expected_type):
    try:
        expected_type(value)
    except ValueError:
        return [(name, "%s value couldn't be converted to comparable representation.\nWe've got '%s'."
                       % (name.capitalize(), value))]
    return []


def validate_range(name, value, min_value, max_value, expected_type):
    if not value:
        return []
    if min_value and expected_type(value) < expected_type(min_value):
        return [(name, "%s is less than template limits (%s < %s)." %
                 (name.capitalize(), value, min_value))]
    if max_value and expected_type(value) > expected_type(max_value):
        return [(name, "%s is larger than template limits (%s > %s)." %
                 (name.capitalize(), value, max_value))]
    return []


class SetDefaultRoute(object):
    def __init__(self, screen, title, settings):
        self.fields = {}
        self.labels = {}
            
    def display(self):
        self.gf = GridForm(self.screen, 'Create VM > Network Settings > Add VIF', 1, 1)
        label = Label('* Choose VIF type')
        items = [('VENET (P-t-P IP)', 0),
                 ('VETH (ether IP)', 1),
                 ('VETH (alias IP)', 2),]
        listbox = Listbox(3, width=30, scroll=1)
        for (k, v) in items:
            listbox.append(k, v)
            bb = ButtonBar(self.screen, (('Cancel', 'cance', 'F12'), 'Ok'))
            hbox = VBox(3)
            hbox.append(label, anchorLeft=1, padding=(0, 0, 0, 1))
            hbox.append(listbox)
            hbox.append(bb, padding=(0, 1, 0, 0))
            self.gf.add(hbox, 0, 0)
        rv = self.gf.runOnce()
        return bb.buttonPressed(rv)
