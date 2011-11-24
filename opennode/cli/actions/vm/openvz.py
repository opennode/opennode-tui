import os
import socket
import operator
import datetime

import libvirt

from opennode.cli import config
from opennode.cli.actions import sysresources as sysres
from opennode.cli.actions.vm import ovfutil
from opennode.cli.utils import SimpleConfigParser, execute
from opennode.cli.actions.vm.config_template import openvz_template

def get_ovf_template_settings(ovf_file):
    settings = read_default_ovf_settings()
    ovf_settings = read_ovf_settings(ovf_file)
    settings.update(ovf_settings)
    settings["vm_id"] = _get_available_ct_id()
    return settings

def validate_template_settings(template_settings, input_settings):
    """ 
    Checks if settings provided by the user match ovf template settings.
    
    @param template_settings: ovf template settings settings.
    @type template_settings: dict

    @param input_settings: settings provided by the user via ui form.
    @type input_settings: dict
    
    @return: a dictionary of errors mapping incorrect parameters to the corresponding error message. 
    @type: dict
    """
    
    def _range_check(setting_name, typecheck=float):
        val = input_settings.get(setting_name, None)
        min_val = input_settings.get("%s_min" % setting_name, None)
        max_val = input_settings.get("%s_max" % setting_name, None)
        if val is None:
            return
        else:
            try:
                typecheck(val)
            except ValueError:
                errors.append((setting_name, "%s value couldn't be converted to comparable representation. We've got %s." %(setting_name, val))) 
        if min_val is not None and val < min_val:
            errors.append((setting_name, "%s is less than template limits (%s < %s)." % (setting_name.capitalize(), val, min_val)))
        if max_val is not None and val > max_val:
            errors.append((setting_name, "%s is larger than template limits (%s > %s)." % (setting_name.capitalize(), val, max_val)))          

      
    def validate_cpu_limit():
        try:
            vcpulimit = int(input_settings["vcpulimit"])
        except ValueError:
            errors.append(("vcpulimit", "CPU count must be integer."))
        else:
            if 0 <= vcpulimit <= 100:
                return True
            else:
                errors.append(("vcpulimit", "CPU usage limit must be between 0 and 100."))
        return False

    
    def validate_ip():
        if input_settings.get("ip_address") is None:
            return True
        try:
            socket.inet_aton(input_settings["ip_address"])
            return True
        except socket.error:
            errors.append(("ip_address", "IP-address format not correct."))
            return False
      
    def validate_nameserver():
        if input_settings.get("nameserver") is None:
            return True
        try:
            socket.inet_aton(input_settings["nameserver"])
            return True
        except socket.error:
            errors.append(("nameserver", "Nameserver format not correct."))
            return False
         
    def validate_password():
        password, password2 = input_settings["passwd"], input_settings["passwd2"]
        if password == password2:
            return True
        else:
            errors.append(("passwd", "Passwords don't match."))
        return False
    
    errors = []
    
    _range_check("memory")
    _range_check("swap")
    _range_check("vcpu", int)
    validate_cpu_limit()
    _range_check("disk", float)
    validate_ip()
    validate_nameserver()
    validate_password()
    
    return errors

def read_default_ovf_settings():
    """ Reads default ovf configuration from file, returns a dictionary of settings."""
    return dict(config.clist('ovf-defaults', 'openvz'))

def read_ovf_settings(ovf_file):
    """ Reads given ovf template configuration file, returns a dictionary of settings."""
    settings = {}
    
    settings["template_name"] = os.path.split(ovf_file.path)[1][:-4]  
    
    vm_type = ovfutil.get_vm_type(ovf_file)
    if vm_type != "openvz":
        raise Exception, "Given template is not compatible with OpenVZ on OpenNode server"
    settings["vm_type"] = vm_type
    
    memory_settings = [
        ("memory_min", ovfutil.get_ovf_min_memory_gb(ovf_file)),
        ("memory_normal", ovfutil.get_ovf_normal_memory_gb(ovf_file)),
        ("memory_max", ovfutil.get_ovf_max_memory_gb(ovf_file))]
    # set only those settings that are explicitly specified in the ovf file (non-null)
    settings.update(dict(filter(operator.itemgetter(1), memory_settings)))
    
    vcpu_settings = [
        ("vcpu_min", ovfutil.get_ovf_min_vcpu(ovf_file)),
        ("vcpu_normal", ovfutil.get_ovf_normal_vcpu(ovf_file)),
        ("vcpu_max", ovfutil.get_ovf_max_vcpu(ovf_file))]
    # set only those settings that are explicitly specified in the ovf file (non-null)
    settings.update(dict(filter(operator.itemgetter(1), vcpu_settings)))
    
    # ??? TODO: apparently need to check disks also?
    return settings

def adjust_setting_to_systems_resources(ovf_template_settings):
    """ 
    Adjusts maximum required resources to match available system resources. 
    NB! Minimum bound is not adjusted.
    """
    st = ovf_template_settings
    st["memory_max"] = str(sysres.get_ram_size_gb())
    st["memory"] = str(min(float(st["memory"]), float(st["memory_max"])))

    st["swap_max"] = str(sysres.get_swap_size_gb())
    st["swap"] = str(min(float(st["swap"]), float(st["swap_max"])))

    st["vcpu_max"] = str(sysres.get_cpu_count())
    st["vcpu"] = str(min(int(st["vcpu"]), int(st["vcpu_max"])))
    
    st["vcpulimit_max"] = str(sysres.get_cpu_usage_limit())
    st["vcpulimit"] = str(min(int(st["vcpulimit"]), int(st["vcpulimit_max"])))
    
    st["disk_max"] = str(sysres.get_disc_space_gb())
    st["disk"] = str(min(float(st["disk"]), float(st["disk_max"])))

    return _check_settings_min_max(st)
    
def _check_settings_min_max(template_settings):
    """ Checks if minimum required resources exceed maximum available resources. """
    errors = []
    st = template_settings
    if float(st["memory_min"]) > float(st["memory_max"]):
        errors.append("Minimum required memory %sGB exceeds total available memory %sGB" %
                      (st["memory_min"], st["memory_max"]))
    if int(st["vcpu_min"]) > int(st["vcpu_max"]):
        errors.append("Minimum required number of vcpus %s exceeds available number %s." %
                      (st["vcpu_min"], st["vcpu_max"]))
    if int(st["vcpulimit_min"]) > int(st["vcpulimit_max"]):
        errors.append("Minimum required vcpu usage limit %s%% exceeds available %s%%." %
                      (st["vcpulimit_min"], st["vcpulimit_max"]))
    if float(st["disk_min"]) > float(st["disk_max"]):
        errors.append("Minimum required disk space %sGB exceeds available %sGB." %
                      (st["disk_min"], st["disk_max"]))
    return errors

def _get_available_ct_id():
    """
    Get next available IF for new OpenVZ CT
    
    @return: Next available ID for new OpenVZ CT
    @rtype: Integer
    """
    return max (100, max(_get_openvz_ct_id_list())) + 1

def _get_openvz_ct_id_list():
    """
    Return a list of current OpenVZ CTs (both running and stopped)

    @return: List of OpenVZ containers on current machine
    @rtype: List
    """
    conn = libvirt.open("openvz:///system")
    return map(int, conn.listDefinedDomains() + conn.listDomainsID())

def _compute_diskspace_hard_limit(soft_limit):
    return soft_limit * 1.1 if soft_limit <= 10 else soft_limit + 1

def generate_ubc_config(settings):
    """ Generates UBC part of  configuration file for VZ container """
    st = settings
    ubc_params = {
        "physpages_barrier": st["memory"],
        "physpages_limit": st["memory"],
        
        "swappages_barrier": st["swap"],
        "swappages_limit": st["swap"],
        
        "diskspace_soft": st["disk"],
        "diskspace_hard": _compute_diskspace_hard_limit(float(st["disk"])),
        
        "diskinodes_soft": float(st["disk"]) *
                           int(config.c("ubc-defaults", "DEFAULT_INODES", "openvz")),
        "diskinodes_hard": round(_compute_diskspace_hard_limit(float(st["disk"])) *
                           int(config.c("ubc-defaults", "DEFAULT_INODES", "openvz"))),
                           
        "quotatime": config.c("ubc-defaults", "DEFAULT_QUOTATIME", "openvz"),
        
        "cpus": st["vcpu"],
        "cpulimit": int(st["vcpulimit"]) * int(st["vcpu"]),
        'cpuunits': config.c("ubc-defaults", "DEFAULT_CPUUNITS", "openvz"),
    }
    # Get rid of zeros where necessary (eg 5.0 - > 5 )
    ubc_params = dict([(key, int(float(val)) if float(val).is_integer() else val) 
                       for key, val in ubc_params.items()])
    ubc_params['time'] = datetime.datetime.today().ctime() 
    return  openvz_template % ubc_params

def generate_nonubc_config(conf_filename, settings):
    """ Generates Non-UBC part of  configuration file for VZ container """
    parser = SimpleConfigParser()
    parser.read(conf_filename)
    config_dict = parser.items()
    # Parameters to read. Others will be generated using ovf settings.
    include_params = set(["VE_ROOT", "VE_PRIVATE", "OSTEMPLATE","ORIGIN_SAMPLE",
                        "IP_ADDRESS", "NAMESERVER","HOSTNAME"])
    config_dict = dict((k, v) for k, v in config_dict.iteritems() if k in include_params)
    config_str = "\n".join("%s=%s" % (k, v) for k, v in config_dict.iteritems()) 
    return config_str

def create_container(ovf_settings):
    """ Creates OpenVZ container """
    
    # create OpenVZ CT
    execute("vzctl create %s --ostemplate %s" % (ovf_settings["vm_id"], ovf_settings["template_name"]))
    execute("chmod 755 /vz/private/%s" % ovf_settings["vm_id"])
    
    # generate ubc and non-ubc configuration
    conf_filename = os.path.join('/etc/vz/conf', "%s.conf" % ovf_settings["vm_id"]) 
    ubc_conf_str = generate_ubc_config(ovf_settings)
    non_ubc_conf_str = generate_nonubc_config(conf_filename, ovf_settings) 
    
    # final configuration is ubc + non-ubc
    openvz_ct_conf = "%s\n%s\n" % (ubc_conf_str, non_ubc_conf_str)
    
    # overwrite configuration
    with open(conf_filename, 'w') as conf_file:
        conf_file.write(openvz_ct_conf)
    execute("chmod 644 %s" % conf_filename)

def deploy(ovf_settings, start = False):
    """ Deploys OpenVZ container """
    #Network configuration for VETH
    #ToDo: implement support for VETH
    #Network configuration for VENET
    execute("vzctl set %s --ipadd %s --save" % (ovf_settings["vm_id"], ovf_settings["ip_address"]))
    execute("vzctl set %s --nameserver %s --save" % (ovf_settings["vm_id"], ovf_settings["nameserver"]))
    execute("vzctl set %s --hostname %s --save" % (ovf_settings["vm_id"], ovf_settings["vm_type"]))
    execute("vzctl set %s --userpasswd root:%s --save" % (ovf_settings["vm_id"], ovf_settings["passwd"]))
    if start:
        start(ovf_settings["vm_id"])

def start(ctid):
    """Start a defined container"""
    execute("vzctl start %s" % ctid)
    
def delete(ctid):
    """Remove a container"""
    execute("vzctl destroy %s" % ctid)
    
def get_available_instances():
    """Return deployed and stopped OpenVZ instances"""
    vzcontainers = execute("vzlist -H -S -o ctid,hostname").split('\n')
    candidates = {}
    for cont in vzcontainers:
        if len(cont.strip()) == 0: break
        cid, hn = cont.strip().split(' ')
        candidates[int(cid)] = "%s (%s)" %(hn, cid)
    return candidates

def get_template_name(ctid):
    """Return a name of the template used for creating specific container"""
    try:
        int(ctid)
    except ValueError:
        raise RuntimeError, "Incorrect format for a container id."
    return execute("vzlist %s -H -o ostemplate" % ctid)

def get_hostname(ctid):
    """Return a hostname of the container"""
    try:
        int(ctid)
    except ValueError:
        raise RuntimeError, "Incorrect format for a container id."
    return execute("vzlist %s -H -o hostname" % ctid)