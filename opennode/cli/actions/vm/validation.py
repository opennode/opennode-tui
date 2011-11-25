import socket
import operator


def check_range(setting_name, settings, typecheck=float):
    val, min_val, max_val = (settings.get(setting_name), settings.get("%s_min" % setting_name),
                             settings.get("%s_max" % setting_name))
    if not val:
        return []
    else:
        try:
            typecheck(val)
        except ValueError:
            return [(setting_name, "%s value couldn't be converted to comparable representation. We've got %s." %(setting_name, val))]
    if min_val and typecheck(val) < typecheck(min_val):
        return [(setting_name, "%s is less than template limits (%s < %s)." % (setting_name.capitalize(), val, min_val))]
    if max_val and typecheck(val) > typecheck(max_val):
        return [(setting_name, "%s is larger than template limits (%s > %s)." % (setting_name.capitalize(), val, max_val))]
    return []

def check_required(setting_name, settings):
    if settings.get(setting_name) is None:
        return [(setting_name, "%s is required" % setting_name)]

def validate_memory(settings):
    return check_required("memory", settings) or check_range("memory", settings)

def validate_cpu(settings):
    return check_required("vcpu", settings) or check_range("vcpu", settings, int)

def validate_disk(settings):
    return check_required("disk", settings) or check_range("disk", settings)

def validate_cpu_limit(settings):
    try:
        vcpulimit = int(settings["vcpulimit"])
    except ValueError:
        return [("vcpulimit", "CPU usage limit be integer.")]
    if not (0 <= vcpulimit <= 100):
        return [("vcpulimit", "CPU usage limit must be between 0 and 100.")]
    return []

def validate_ip(settings):
    if settings.get("ip_address"):
        try:
            socket.inet_aton(settings["ip_address"])
        except socket.error:
            return [("ip_address", "IP-address format not correct.")]
    return []

def validate_hostname(settings):
    if settings.get("hostname") is None:
        return [("hostname", "Hostname cannot be missing")]
    if len(settings.get("hostname")) < 1:
        return [("hostname", "Hostname cannot be 0-length")]
    return []

def validate_nameserver(settings):
    if settings.get("nameserver"):
        try:
            socket.inet_aton(settings["nameserver"])
        except socket.error:
            return [("nameserver", "Nameserver format not correct.")]
    return []

def validate_password(settings):
    password, password2 = settings["passwd"], settings["passwd2"]
    if password != password2:
        return [("passwd", "Passwords don't match.")]
    return []

validators = {
    "passwd": validate_password,
    "nameserver": validate_nameserver,
    "hostname": validate_hostname,
    "ip_address": validate_ip,
    "vcpulimit": validate_cpu_limit,
    "memory": validate_memory,
    "vcpu":  validate_cpu,
    "cpu":  validate_cpu,
    "disk": validate_disk
}

def validate_settings(settings, attribute_filter = None):
    """
    Checks if settings provided by a user match ovf template limits.

    @param settings: settings provided by the user via ui form with corresponding min/max values from ovf template file.
    @type input_settings: dict

    @param attribute_filter: which attributes from settings to check
    @type attribute_filter: list

    @return: a list of errors mapping incorrect parameters to the corresponding error message.
    @type: list
    """
    filter = set(attribute_filter or validators.keys())
    return reduce(operator.add, [validators[key](settings) for key, val in settings.items() if key in filter], [])
