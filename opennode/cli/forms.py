""" Forms for OpenNode Terminal User Interface """

import operator

from snack import Textbox, Button, GridForm

from opennode.cli.fields import FloatField, IntegerField, StringField
from opennode.cli.fields import PasswordField, IpField, RadioBarField
from opennode.cli.fields import BindMountsField, CheckboxField
from opennode.cli.fields import HostnameField
from opennode.cli.fields import validate_range


class Form(object):
    errors, data = [], {}

    def __init__(self, screen, title, fields):
        self.title, self.screen, self.fields = title, screen, fields

    def validate(self):
        self.errors = reduce(operator.add, [field.errors for field in self.fields
                                            if not field.validate()], [])
        if not self.errors:
            self.data = dict([(field.name, field.value()) for field in self.fields])
            return True
        else:
            return False

    def display(self):
        pass


class KvmForm(Form):

    def __init__(self, screen, title, settings):
        self.memory = FloatField("memory", settings["memory"], settings["memory_min"],
                                 settings["memory_max"])
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
        self.memory = FloatField("memory", settings["memory"], settings["memory_min"],
                                 settings["memory_max"])
        self.swap = FloatField("swap", settings["swap"], settings["swap_min"], settings["swap_max"])
        self.vcpu = FloatField("vcpu", settings["vcpu"], settings["vcpu_min"], settings["vcpu_max"])
        self.vcpulimit = IntegerField("vcpulimit", settings["vcpulimit"], settings["vcpulimit_min"],
                                      settings["vcpulimit_max"])
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
        self.memory_min = FloatField("memory_min", settings.get("memory_min", ""),
                                     display_name="min memory", required=False)
        self.memory_max = FloatField("memory_max", settings.get("memory_max", ""),
                                     display_name="max memory", required=False)
        self.vcpu = FloatField("vcpu", settings["vcpu"])
        self.vcpu_min = FloatField("vcpu_min", settings.get("vcpu_min", ""),
                                   display_name="min vcpu", required=False)
        self.vcpu_max = FloatField("vcpu_max", settings.get("vcpu_max", ""),
                                   display_name="max vcpu", required=False)
        self.disk = FloatField("disk", settings["disk"])
        self.ostemplate = StringField("ostemplate", settings.get("ostemplate", ""))
        Form.__init__(self, screen, title, [self.memory, self.memory_min, self.memory_max, self.vcpu,
                                            self.vcpu_min, self.vcpu_max, self.disk, self.ostemplate])

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
        self.memory_min = FloatField("memory_min", settings.get("memory_min", ""),
                                     display_name="min memory", required=False)
        self.memory_max = FloatField("memory_max", settings.get("memory_max", ""),
                                     display_name="max memory", required=False)
        self.vcpu = FloatField("vcpu", settings["vcpu"])
        self.vcpu_min = FloatField("vcpu_min", settings.get("vcpu_min", ""),
                                   display_name="min vcpu", required=False)
        self.vcpu_max = FloatField("vcpu_max", settings.get("vcpu_max", ""),
                                   display_name="max vcpu", required=False)
        self.username = StringField("username", settings.get("username", ''), display_name="username")
        self.password = PasswordField("passwd", settings.get("passwd", ''), display_name="password")
        self.password2 = PasswordField("passw2", settings.get("passwd", ''), display_name="password")
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
            (Textbox(20, 1, "Default admin:", 0, 0), self.username),
            separator,
            (Textbox(20, 1, "Root password:", 0, 0), self.password),
            (Textbox(20, 1, "Root password x2:", 0, 0), self.password2),
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
            if (self.password.validate() and self.password2.validate() and
                    self.password.value() != self.password2.value()):
                self.errors.extend(("passwd", "Passwords don't match."))

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
        self.vcpulimit = IntegerField("vcpulimit", settings["vcpulimit"],
                                      min_value=0, max_value=100)
        self.onboot = CheckboxField("onboot", settings.get("onboot", 0), display_name="Start on boot")
        self.ctid = IntegerField('ctid', settings['ctid'],
                                 display_name='VEID', required=False)
        self.hostname = StringField("hostname", settings.get("name", ""))
        Form.__init__(self, screen, title, [self.memory, self.vcpu, self.disk, self.ioprio, self.hostname,
                                            self.bind_mounts, self.swap, self.onboot, self.bootorder,
                                            self.vcpulimit, self.ctid])

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
            (Textbox(20, 1, "Hostname:", 0, 0), self.hostname),
            separator,
            (Textbox(20, 1, "", 0, 0), self.onboot),
            separator,
            (Textbox(20, 1, "Boot order:", 0, 0), self.bootorder),
            separator,
            (Textbox(20, 1, "VEID:", 0, 0), self.ctid),
            separator,
            (button_exit, button_save)
        ]
        form = GridForm(self.screen, self.title, 2, len(rows))
        for i, row in enumerate(rows):
            for j, cell in enumerate(row):
                form.add(cell, j, i)
        return form.runOnce() != button_exit

    def validate(self):
        # TODO disallow decrease of disk size, which would break OS
        Form.validate(self)
        bm_valid = self.bind_mounts.validate()
        if bm_valid:
            error_str = "\n".join([s[1] for s in bm_valid])
            self.errors.append(("bind_mounts", "%s" % error_str))
        if self.memory.value() < self.settings["memory_min"]:
            err_msg = ("Memory size can not be lower than minimum defined in template: %s GB" %
                       self.settings["memory_min"])
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
            (button_save, button_exit)]
        form = GridForm(self.screen, self.title, 2, len(rows))
        for i, row in enumerate(rows):
            for j, cell in enumerate(row):
                form.add(cell, j, i)
        return form.runOnce() != button_exit

    def validate(self):
        Form.validate(self)
        return not self.errors


class GenericTemplateEditForm(Form):

    separator = (Textbox(20, 1, "", 0, 0), Textbox(20, 1, "", 0, 0))

    def _define_fields(self, settings):
        self.memory = FloatField("memory", settings["memory"])
        self.memory_min = FloatField("memory_min", settings.get("memory_min", ""),
                                     display_name="min memory", required=False)
        self.vcpu = FloatField("vcpu", settings["vcpu"])
        self.vcpu_min = FloatField("vcpu_min", settings.get("vcpu_min", ""),
                                   display_name="min vcpu", required=False)
        self.template_name = StringField('template_name', settings.get('template_name'),
                                         display_name='template name', required=False)
        return [self.memory,
                self.memory_min,
                self.vcpu,
                self.vcpu_min,
                self.template_name]

    def _define_view(self, button_save, button_exit):
        rows = [
            (Textbox(20, 1, "Template name:", 0, 0), self.template_name),
            self.separator,
            (Textbox(20, 1, "Memory size (GB):", 0, 0), self.memory),
            (Textbox(20, 1, "Min memory size (GB):", 0, 0), self.memory_min),
            self.separator,
            (Textbox(20, 1, "Number of CPUs:", 0, 0), self.vcpu),
            (Textbox(20, 1, "Min number of CPUs:", 0, 0), self.vcpu_min),
            self.separator,
            (button_exit, button_save)
        ]
        return rows

    def __init__(self, screen, title, settings):
        self.settings = settings
        super(GenericTemplateEditForm, self).__init__(screen, title,
                                                      self._define_fields(settings))

    def display(self):
        button_save, button_exit = Button("Edit"), Button("Cancel")
        rows = self._define_view(button_save, button_exit)
        form = GridForm(self.screen, self.title, 2, len(rows))
        for i, row in enumerate(rows):
            for j, cell in enumerate(row):
                form.add(cell, j, i)
        return form.runOnce() != button_exit


class KvmTemplateEditForm(GenericTemplateEditForm):

    def _define_fields(self, settings):
        self.username = StringField('username', settings.get('username', ''), display_name='username',
                                    required=False)
        self.password = PasswordField('passwd', settings['passwd'],
                                      display_name='password', required=True)
        self.password2 = PasswordField('passwd2', settings['passwd'],
                                             display_name='password', required=True)
        fields = super(KvmTemplateEditForm, self)._define_fields(settings)
        fields.append(self.username)
        fields.append(self.password)
        fields.append(self.password2)
        return fields

    def _define_view(self, button_save, button_exit):
        rows = super(KvmTemplateEditForm, self)._define_view(button_save, button_exit)
        rows.insert(-2, self.separator)
        rows.insert(-2, (Textbox(20, 1, 'Default admin:', 0, 0), self.username))
        rows.insert(-2, self.separator)
        rows.insert(-2, (Textbox(20, 1, 'Password:', 0, 0), self.password))
        rows.insert(-2, (Textbox(20, 1, 'Password x2:', 0, 0), self.password2))
        return rows
