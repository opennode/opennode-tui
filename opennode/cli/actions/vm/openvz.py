import string

import os
import libvirt
from ovf.OvfFile import OvfFile

from opennode.cli.config2 import openvz_config 
from opennode.cli.actions import sysresources as sysres
from opennode.cli.actions.vm import ovfutil

def get_ovf_template_settings(ovf_file):
    settings = get_default_ovf_settings()
    ovf_settings = read_ovf_settings(ovf_file)
    settings.update(ovf_settings)
    settings["vm_id"] = _get_available_ct_id()
    return settings  

def validate_template_settings(template_settings, input_settings):
    errors = []
    
    def validate_memory():
        try:
            memory = float(input_settings["memory"])
        except ValueError:
            errors.append(("memory", "Memory size must be integer or decimal."))
        else:
            if float(template_settings["memory_min"]) <= memory <= \
                float(template_settings["memory_max"]):
                return True
            else:
                errors.append(("memory", "Memory size out of template limits."))
        return False
      
    def validate_cpu():
        try:
            vcpu = int(input_settings["vcpu"])
        except ValueError:
            errors.append(("vcpu", "CPU count must be integer."))
        else:
            if int(template_settings["vcpu_min"]) <= vcpu <= \
                int(template_settings["vcpu_max"]):
                return True
            else:
                errors.append(("vcpu", "CPU count out of template limits."))
        return False
      
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
    
    def validate_disk():
        try:
            disk = float(input_settings["disk"])
        except ValueError:
            errors.append(("disk", "Disk size must be integer."))
        else:
            if float(template_settings["disk_min"]) <= disk <= \
                float(template_settings["disk_max"]):
                return True
            else: 
                errors.append(("disk", "Disk size out of template limits."))
        return False
    
    def validate_ip():
        if not _check_ip_format(input_settings["ip_address"]):
            errors.append(("ip_address", "IP-address format not correct."))
            return False
        else:
            return True
      
    def validate_nameserver(): 
        if not _check_ip_format(input_settings["nameserver"]):
            errors.append(("nameserver", "Nameserver format not correct."))
            return False
        else:
            return True
      
    def validate_password():
        password, password2 = input_settings["passwd"], input_settings["passwd2"] 
        if len(password) < 6:
            errors.append(("passwd", "Password must be at least 6 characters long."))
        elif password != password2: 
            errors.append(("passwd", "Passwords don't match."))
        else:
            return True
        return False
    
    def _check_ip_format(ip):
        item_list = ip.split(".")
        if len(item_list)!= 4:
            return False
        for item in item_list:
            try:
                if not (0 <= int(item) <= 255) or len(item) > 3:
                    return False
            except:
                return False
        return True
    
    validate_memory()
    validate_cpu()
    validate_cpu_limit()
    validate_disk()
    validate_ip()
    validate_nameserver()
    validate_password()
    
    return errors

def get_default_ovf_settings():
    return dict(openvz_config.clist("general"))

def read_ovf_settings(ovf_file):
    """ Reads ovf configuration file, returns a dictionary of settings. """
    settings = {}

    settings["template_name"] = os.path.split(ovf_file.path)[1][:-4]  
    
    vm_type = ovf_file.document.getElementsByTagName("vssd:VirtualSystemType")[0].firstChild.nodeValue
    if vm_type != "openvz":
        raise Exception, "Given template is not compatible with OpenVZ on OpenNode server"
    settings["vm_type"] = vm_type
    
    memory = zip(["memory_min", "memory_normal", "memory_max"], 
                 ovfutil.get_ovf_memory_gb(ovf_file))
    memory = filter(lambda item: item[1] != None, memory)
    settings.update(dict(memory))
    
    vcpu = zip(["vcpu_min", "vcpu_normal", "vcpu_max"], 
                ovfutil.get_ovf_vcpu(ovf_file))
    vcpu = filter(lambda item: item[1] != None, vcpu)
    settings.update(dict(vcpu))
    
    # ??? TODO: apparently need to check disks also?
    return settings

def adjust_setting_to_systems_resources(ovf_template_settings):
    st = ovf_template_settings
    st["vcpu_max"] = str(min(sysres.get_cpu_count(), int(st["vcpu_max"])))
    st["vcpu"] = str(min(int(st["vcpu"]), int(st["vcpu_max"])))
    
    st["vcpulimit_max"] = str(min(sysres.get_cpu_usage_limit(), int(st["vcpulimit_max"])))
    st["vcpulimit"] = str(min(int(st["vcpulimit"]), int(st["vcpulimit_max"])))
    
    st["memory_max"] = str(min(sysres.get_ram_size_gb(), float(st["memory_max"])) )
    st["memory"] = str(min(float(st["memory"]), float(st["memory_max"])))
    
    st["disk_max"] = str(min(sysres.get_disc_space_gb(), float(st["disk_max"])))
    st["disk"] = str(min(float(st["disk"]), float(st["disk_max"])))
    st["disk_min"] = str(max(sysres.get_min_disc_space_gb(st["vm_id"]), float(st["disk_min"])))
    return _check_settings_min_max(st)
    
def _check_settings_min_max(template_settings):
    """ Check if minimum required resources exceed maximum available resources. """
    errors = []
    st = template_settings
    if float(st["memory_min"]) > float(st["memory_max"]):
        errors.append("Minimum required memory %sGB exceeds total available memory %sGB" %\
                      (st["memory_min"], st["memory_max"]))
    if int(st["vcpu_min"]) > int(st["vcpu_max"]):
        errors.append("Minimum required number of vcpus %s exceeds available number %s." %\
                      (st["vcpu_min"], st["vcpu_max"]))
    if int(st["vcpulimit_min"]) > int(st["vcpulimit_max"]):
        errors.append("Minimum required vcpu usage limit %s%% exceeds available %s%%." %\
                      (st["vcpulimit_min"], st["vcpulimit_max"]))
    if float(st["disk_min"]) > float(st["disk_max"]):
        errors.append("Minimum required disk space %sGB exceeds available %sGB." %\
                      (st["disk_min"], st["disk_max"]))
    return errors
def _get_available_ct_id():
    """
    Get next available IF for new OpenVZ CT
    
    @return: Next available ID for new OpenVZ CT
    @rtype: Integer
    """
    return max(_get_openvz_ct_id_list()) + 1

def _get_openvz_ct_id_list():
    """
    Return a list of current OpenVZ CTs (both running and stopped)

    @return: List of OpenVZ CTs on current machine
    @rtype: List
    """
    conn = libvirt.open("openvz:///system")
    return map(int, conn.listDefinedDomains() + conn.listDomainsID())
