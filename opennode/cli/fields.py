import re
import os

from snack import Entry, Checkbox, RadioBar
import socket


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
