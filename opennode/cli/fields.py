import os
import re
import socket
from snack import Entry, Listbox
from snack import Checkbox, RadioBar


class CheckboxField(Checkbox):

    def __init__(self, name, default, display_name=None):
        self.name = name
        self.display_name = display_name or name
        Checkbox.__init__(self, "%s" % self.display_name, int(default))

    def validate(self):
        return True

    @classmethod
    def create_with_settings(cls, name, settings, **kw):
        return CheckboxField(name, kw.get(name, int(settings.get(name, 0))), **kw)


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

    @classmethod
    def create_with_settings(cls, name, settings, **kw):
        return StringField(name, kw.get(name, settings.get(name, '')), **kw)


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

    @classmethod
    def create_with_settings(cls, name, settings, **kw):
        return BindMountsField(name, kw.get(name, settings.get(name, '')), **kw)


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

    @classmethod
    def create_with_settings(cls, name, settings, **kw):
        return IpField(name, kw.get(name, settings.get(name, '')), **kw)


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

    @classmethod
    def create_with_settings(cls, name, settings, **kw):
        return HostnameField(name, kw.get(name, settings.get(name, '')), **kw)


class PasswordField(Field):
    def __init__(self, name, default, required=True, width=20, display_name=None):
        Field.__init__(self, name, default, width, required=required,
                       password=1, display_name=display_name)

    def validate(self):
        # TODO: cracklib?
        return Field.validate(self)

    @classmethod
    def create_with_settings(cls, name, settings, **kw):
        return PasswordField(name, kw.get(name, settings.get(name, '')), **kw)


class IntegerField(Field):
    def __init__(self, name, default, min_value=None, max_value=None,
                 width=20, display_name=None, required=True):
        Field.__init__(self, name, default, width, min_value=min_value,
                       max_value=max_value, expected_type=int, display_name=display_name,
                       required=required)

    @classmethod
    def create_with_settings(cls, name, settings, **kw):
        return IntegerField(name, kw.get(name, settings.get(name, '')),
                            min_value=settings.get(name + '_min', kw.get(name + '_min', '')),
                            max_value=settings.get(name + '_max', kw.get(name + '_max', '')), **kw)


class FloatField(Field):
    def __init__(self, name, default, min_value=None, max_value=None,
                 width=20, display_name=None, required=True):
        Field.__init__(self, name, default, width, min_value=min_value,
                       max_value=max_value, expected_type=float, display_name=display_name,
                       required=required)

    @classmethod
    def create_with_settings(cls, name, settings, width=20, **kw):
        return FloatField(name, kw.get(name, settings.get(name, '')),
                          min_value=settings.get(name + '_min', kw.get(name + '_min', '')),
                          max_value=settings.get(name + '_max', kw.get(name + '_max', '')), **kw)


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
