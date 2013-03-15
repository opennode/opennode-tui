#!/usr/bin/env python

import operator
from snack import Grid, Entry, Listbox, colorsets, FLAG_DISABLED, Textbox, Button
from snack import GridForm, Label, ButtonBar
from opennode.cli.actions import sysresources as sysres
from opennode.cli.forms import FloatField, IntegerField, PasswordField, StringField, IpField, CheckboxField
from opennode.cli.forms import OneLineListbox, BindMountsField, RadioBarField, validate_range, HostnameField


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
            self.data = dict([(self.fields[field].name, self.fields[field].value())
                              for field in self.fields])
            return True
        else:
            return False

    def display(self):
        pass


class BaseForm(Form):

    def _set_fields(self, settings):
        self.fields = {}

    def _set_labels(self, settings):
        self.labels = {}

    def __init__(self, screen, title, settings):
        self._set_fields(settings)
        self._set_labels(settings)
        Form.__init__(self, screen, title, self.fields)


class CreateVM(BaseForm):

    def _set_fields(self, settings):
        _proto_fields = {
            'memory': (FloatField, {'width': 6}),
            'swap': (FloatField, {'width': 6}),
            'disk': (FloatField, {'width': 6}),
            'vcpu': (IntegerField, {'width': 6}),
            'hostname': (StringField,  {'width': 15}),
            'ip_address': (IpField,  {'width': 16}),
            'nameserver': (IpField,  {'width': 36}),
            'passwd': (PasswordField,  {'width': 36}),
            'passwd2': (PasswordField, {'width':  36}),
            'startvm': (CheckboxField,  {'display_name': 'Start VM'}),
            'onboot': (CheckboxField, {'display_name': 'Start on boot'})}

        self.fields = {}
        for k, v in _proto_fields.iteritems():
            ftype, kw = v
            self.fields[k] = ftype.create_with_settings(k, settings, **kw)

    def _set_labels(self, settings):
        self._proto_labels = ['disk_max',
                              'disk_min',
                              'swap_max',
                              'swap_min',
                              'memory_max',
                              'memory_min',
                              'vcpu_min',
                              'vcpu_max',]

        self.labels = dict([(k, str(settings.get(k, ''))) for k in self._proto_labels])

    def __init__(self, screen, title, settings):
        BaseForm.__init__(self, screen, title, settings)

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


class EditVM(BaseForm):

    def _set_fields(self, settings):
        memory_max = min(sysres.get_ram_size_gb(),
                         float(settings.get("memory_max", 10 ** 30)))
        swap_max = min(sysres.get_swap_size_gb(),
                       float(settings.get("swap_max", 10 ** 30)))
        disk_max = min(sysres.get_disc_space_gb(),
                       float(settings.get("disk_max", 10 ** 30)))
        vcpu_max = min(sysres.get_cpu_count(),
                       int(settings.get("vcpu_max", 10 ** 10)))

        _proto_fields = {
            'memory': (FloatField, {'width': 6, 'memory_max': memory_max,
                                    'memory': '%.6g' % float(settings['memory'])}),
            'swap': (FloatField, {'width': 6, 'swap_max': swap_max,
                                  'swap': '%.6g' % float(settings['swap'])}),
            'disk': (FloatField, {'width': 6,
                                  'disk': '%.6g' % float(settings['diskspace']['/']),
                                  'disk_max': disk_max,
                                  'disk_min': settings.get('disk_min', 2.0)}),
            'vcpu': (IntegerField, {'width': 6, 'vcpu_max': vcpu_max}),
            'name': (StringField,  {'width': 15}),
            'ip_address': (IpField,  {'width': 16, 'ip_address': settings['interfaces'][0]['ipaddr']}),
            'nameserver': (IpField,  {'width': 36}),
            'onboot': (CheckboxField, {'display_name': 'Start on boot'})}

        self.fields = {}
        for k, v in _proto_fields.iteritems():
            ftype, kw = v
            self.fields[k] = ftype.create_with_settings(k, settings, **kw)

    def _set_labels(self, settings):
        _proto_labels = {'disk_max': min(sysres.get_disc_space_gb(),
                                         float(settings.get("disk_max", 10 ** 30))),
                         'disk_min': 2.0,
                         'swap_max': min(sysres.get_swap_size_gb(),
                                         float(settings.get("swap_max", 10 ** 30))),
                         'swap_min': 0,
                         'memory_max': min(sysres.get_ram_size_gb(),
                                           float(settings.get("memory_max", 10 ** 30))),
                         'memory_min': 0.1,
                         'vcpu_min': 1,
                         'vcpu_max': min(sysres.get_cpu_count(),
                                         int(settings.get("vcpu_max", 10 ** 10))),}

        self.labels = dict([(k, str(settings.get(k, v))) for k,v in _proto_labels.values()])

    def __init__(self, screen, title, settings):
        BaseForm.__init__(self, screen, title, settings)

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


class NetworkSettings(BaseForm):

    def _set_fields(self, settings):
        self.fields = {
            'hostname': StringField('hostname', settings.get('hostname', ''), width = 18),
            'ipv6': CheckboxField('ipv6', bool(settings.get('ipv6', False)), display_name = 'IPv6 Enabled'),
            'nameserver': IpField('nameserver', settings.get('nameserver', ''), width = 36),}

    def __init__(self, screen, title, settings):
        self.VIFS = Listbox(4, scroll=1)

        BaseForm.__init__(self, screen, title, self.fields)

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
                                            '%-15s' % iface.get('ipaddr', iface.get('ipaddr', '')), gw]))
        for nr, iface in enumerate(net_ifaces):
            self.VIFS.insert(iface, nr, 0)

        self.labels['default_route'] = ''
        for iface in self.interfaces:
            # TODO: if we have DHCP enabled iface then how to get that gw value
            if iface.get('default', '') == 'yes' and iface['gw']:
                self.labels['default_route'] = 'default via %s dev %s' % (iface['gw'], iface['ifname'])
                break

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


class AddVIF(BaseForm):

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

    def __init__(self, screen, title, settings):
        BaseForm.__init__(self, screen, title, settings)


class EditVIF(BaseForm):

    def _set_fields(self, settings):
        self.fields = {
            'managed': CheckboxField('managed', bool(self.interface.get('managed', True)),
                                     display_name='Managed'),
            'dhcp': CheckboxField('dhcp', bool(self.interface.get('dhcp', False)), display_name='DHCP'),
            'vif_mac': StringField('vif_mac', self.interface.get('vif_mac', '(autogenerated)'),
                                   required=False, width=18),
            'mac': StringField('mac', self.interface.get('mac', '(autogenerated)'),
                               required = False, width=18),
            'ipaddr': IpField('ipaddr', self.interface.get('ipaddr', ''), width=16),
            'mask': IpField('mask', self.interface.get('mask', ''), required = False, width=16),
            'gw': IpField('gw', self.interface.get('gw', ''), required = False, width=16),}

    def _set_labels(self, settings):
        self.labels = {}
        # TODO: add vlan id and bw controls
        self.labels['name'] = self.interface.get('name', '')
        self.labels['host_bridge'] = self.interface.get('host_ifname', '')

    def __init__(self, screen, title, settings):
        self.interface = self.settings['interfaces'][settings['editvif']]
        self.settings = settings
        BaseForm.__init__(self, screen, title, settings)

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


class VenetSettings(BaseForm):

    def _set_fields(self):
        self.fields = {}
        self.fields['ipaddr'] = IpField('ipaddr', '', width = 16)

    def __init__(self, screen, title, settings):
        BaseForm.__init__(self, screen, title, settings)
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


class Resources(BaseForm):

    # TODO: add support for VCPU masks, UBC limits
    def _set_fields(self, settings):
        self.fields = {}
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

    def _set_labels(self, settings):
        self.labels = {}
        self.labels['vcpu_min'] = str(settings.get('vcpu_min', 1))
        self.labels['vcpu_max'] = str(settings.get('vcpu_max', ''))

    def __init__(self, screen, title, settings):
        BaseForm.__init__(self, screen, title, settings)

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


class Storage(BaseForm):

    def _set_fields(self, settings):
        self.fields = {}
        self.fields['bind_mounts'] = BindMountsField('bind_mounts',
                                                     settings.get('bind_mounts', ''),
                                                     required = False,
                                                     width = 25)
        ioprio_values = [('Low', 0),
                         ('Default', 4),
                         ('High', 7)]
        self.fields['ioprio'] = OneLineListbox('ioprio', ioprio_values, 25, settings.get('ioprio', None))

    def _set_labels(self, settings):
        self.labels = {}

    def __init__(self, screen, title, settings):
        BaseForm.__init__(self, screen, title, settings)

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


class KvmForm(BaseForm):

    def _set_fields(self, settings):
        self.fields = {'memory': FloatField("memory", settings["memory"], settings["memory_min"],
                                            settings["memory_max"]),
                       'vcpu': IntegerField("vcpu", settings["vcpu"], settings["vcpu_min"],
                                            settings["vcpu_max"]),
                       'hostname': StringField("hostname", settings.get("hostname", ""))}

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
            (button_save, button_exit)]

        form = GridForm(self.screen, self.title, 2, len(rows))

        for i, row in enumerate(rows):
            for j, cell in enumerate(row):
                form.add(cell, j, i)
        return form.runOnce() != button_exit


class OpenvzForm(BaseForm):

    def _set_fields(self, settings):
        self.memory = FloatField("memory", settings["memory"],
                                 settings["memory_min"], settings["memory_max"])
        self.swap = FloatField("swap", settings["swap"], settings["swap_min"], settings["swap_max"])
        self.vcpu = FloatField("vcpu", settings["vcpu"], settings["vcpu_min"], settings["vcpu_max"])
        self.vcpulimit = IntegerField("vcpulimit", settings["vcpulimit"],
                                      settings["vcpulimit_min"], settings["vcpulimit_max"])
        self.disk = FloatField("disk", settings["disk"], settings["disk_min"], settings["disk_max"])
        self.bind_mounts = BindMountsField("bind_mounts", settings["bind_mounts"], required=False)
        self.hostname = StringField("hostname", settings.get("hostname", ""))
        self.ip_address = IpField("ip_address", settings["ip_address"], display_name="IP address")
        self.nameserver = IpField("nameserver", settings["nameserver"])
        self.password = PasswordField("passwd", settings["passwd"], display_name="password")
        self.password2 = PasswordField("passw2", settings["passwd"], display_name="password")
        self.ostemplate = StringField("ostemplate", settings["ostemplate"], display_name="OS template")
        self.startvm = CheckboxField("startvm", settings.get("startvm", 0), display_name="Start VM")
        self.onboot = CheckboxField("onboot", settings.get("onboot", 0), display_name="Start on boot")

        self.fields = {'memory': self.memory,
                       'swap': self.swap,
                       'vcpu': self.vcpu,
                       'vcpulimit': self.vcpulimit,
                       'disk': self.disk,
                       'bind_mounts': self.bind_mounts,
                       'hostname': self.hostname,
                       'ip_address': self.ip_address,
                       'nameserver': self.nameserver,
                       'password': self.password,
                       'password2': self.password2,
                       'ostemplate': self.ostemplate,
                       'startvm': self.startvm,
                       'onboot': self.onboot,}

    def __init__(self, screen, title, settings):
        BaseForm.__init__(self, screen, title, settings)
        self.fields['ioprio'] = RadioBarField("ioprio", screen, [('Low    ', 0, settings["ioprio"] == 0),
                                                                 ('Default', 4, settings["ioprio"] == 4),
                                                                 ('High   ', 7, settings["ioprio"] == 7)])
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


class BaseTemplateForm(BaseForm):

    separator = (Textbox(20, 1, "", 0, 0), Textbox(20, 1, "", 0, 0))

    def _set_fields(self, settings):
        self.memory = FloatField("memory", settings["memory"])
        self.memory_min = FloatField("memory_min", settings.get("memory_min", ""),
                                     display_name="min memory", required=False)
        self.memory_max = FloatField("memory_max", settings.get("memory_max", ""),
                                     display_name="max memory", required=False)
        self.vcpu = FloatField("vcpu", settings["vcpu"])
        self.vcpu_min = FloatField("vcpu_min", settings.get("vcpu_min", ""),
                                   display_name="min vcpu", required=False)
        self.vcpu_max = FloatField("vcpu_max", settings.get("vcpu_max", ""),
                                   display_name="max vcpu", required=False)

        self.fields = {'memory': self.memory,
                       'memory_min': self.memory_min,
                       'memory_max': self.memory_max,
                       'vcpu': self.vcpu,
                       'vcpu_min': self.vcpu_min,
                       'vcpu_max': self.vcpu_max,}

        self.button_save = Button("Create")
        self.button_exit = Button("Back")
        self.layout = [
            (Textbox(20, 1, "Memory size (GB):", 0, 0), self.memory),
            (Textbox(20, 1, "Min memory size (GB):", 0, 0), self.memory_min),
            (Textbox(20, 1, "Max memory size (GB):", 0, 0), self.memory_max),
            self.separator,
            (Textbox(20, 1, "Number of CPUs:", 0, 0), self.vcpu),
            (Textbox(20, 1, "Min number of CPUs:", 0, 0), self.vcpu_min),
            (Textbox(20, 1, "Max number of CPUs:", 0, 0), self.vcpu_max),
            self.separator,
            (self.button_exit, self.button_save)
        ]

    def __init__(self, screen, title, settings):
        BaseForm.__init__(self, screen, title, settings)

    def display(self):
        form = GridForm(self.screen, self.title, 2, len(self.layout))
        for i, row in enumerate(self.layout):
            for j, cell in enumerate(row):
                form.add(cell, j, i)
        return form.runOnce() != self.button_exit

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


class OpenvzTemplateForm(BaseTemplateForm):

    def _set_fields(self, settings):
        BaseTemplateForm._set_fields(self, settings)
        self.disk = FloatField("disk", settings["disk"])
        self.ostemplate = StringField("ostemplate", settings.get("ostemplate", ""))
        self.fields = {'disk' : self.disk,
                       'ostemplate': self.ostemplate}
        separator = (Textbox(20, 1, "", 0, 0), Textbox(20, 1, "", 0, 0))
        self.layout[6:7] = [separator,
            (Textbox(20, 1, "Disk size (GB):", 0, 0), self.disk),
            separator,
            (Textbox(20, 1, "OS template:", 0, 0), self.ostemplate),]

    def __init__(self, screen, title, settings):
        BaseForm.__init__(self, screen, title, settings)


class KvmTemplateForm(BaseTemplateForm):

    def __init__(self, screen, title, settings):
        BaseForm.__init__(self, screen, title, settings)


class OpenvzModificationForm(BaseForm):

    def _set_fields(self, settings):
        self.settings = settings
        self.memory = FloatField("memory", float(settings["memory"]) / 1024)
        self.swap = FloatField("swap", float(settings["swap"]) / 1024)
        self.vcpu = IntegerField("vcpu", settings["vcpu"])
        self.bootorder = IntegerField("bootorder", settings.get("bootorder"), required=False)
        self.disk = FloatField("diskspace", float(settings["diskspace"]["/"]) / 1024)
        self.bind_mounts = BindMountsField("bind_mounts", settings["bind_mounts"], required=False)
        self.vcpulimit = IntegerField("vcpulimit", settings["vcpulimit"], min_value=0)
        self.onboot = CheckboxField("onboot", settings.get("onboot", 0), display_name="Start on boot")

        self.fields = {'memory': self.memory,
                       'swap': self.swap,
                       'vcpu': self.vcpu,
                       'bootorder': self.bootorder,
                       'disk': self.disk,
                       'bind_mounts': self.bind_mounts,
                       'vcpulimit': self.vcpulimit,
                       'onboot': self.onboot,}

    def __init__(self, screen, title, settings):
        BaseForm.__init__(self, screen, title, settings)
        self.ioprio = RadioBarField("ioprio", screen, [('Low    ', 0, settings["ioprio"] == 0),
                                                       ('Default', 4, settings["ioprio"] == 4),
                                                       ('High   ', 7, settings["ioprio"] == 7)])
        self.fields.update({'ioprio': self.ioprio})

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
        Form.validate(self)
        # TODO disallow decrease of disk size, which would break OS
        bm_valid = self.bind_mounts.validate()
        if bm_valid:
            error_str = "\n".join([s[1] for s in bm_valid])
            self.errors.append(("bind_mounts", "%s" % error_str))
        if self.memory.value() < self.settings["memory_min"]:
            err_msg = ("Memory size can not be lower than minimum defined in template: %s GB" %
                       self.settings["memory_min"])
            self.errors.append(("memory", err_msg))
        return not self.errors


class OpenVZMigrationForm(BaseForm):

    def _set_fields(self, settings):
        self.target = HostnameField("target host", '')
        self.live = CheckboxField("live", default=0, display_name='(risky)')
        self.fields = {'target': self.target,
                       'live': self.live}

    def __init__(self, screen, title, settings):
        BaseForm.__init__(self, screen, title, settings)

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

# ------------- Field widgets --------------

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
