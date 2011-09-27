import os
import socket
import operator
import string

import cracklib
import libvirt
from ovf.OvfFile import OvfFile

from opennode.cli.config2 import openvz_config 
from opennode.cli.actions import sysresources as sysres
from opennode.cli.actions.vm import ovfutil

def get_ovf_template_settings(ovf_file):
    settings = read_default_ovf_settings()
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
        try:
            socket.inet_aton(input_settings["ip_address"])
            return True
        except socket.error:
            errors.append(("ip_address", "IP-address format not correct."))
            return False
      
    def validate_nameserver():
        try:
            socket.inet_aton(input_settings["nameserver"])
            return True
        except socket.error:
            errors.append(("nameserver", "Nameserver format not correct."))
            return False
         
    def validate_password():
        password, password2 = input_settings["passwd"], input_settings["passwd2"]
        try:
            cracklib.VeryFascistCheck(password)
        except ValueError, err:
            errors.append(("passwd", "Password: %s" % err))
        else:
            if password == password2:
                return True
            else:
                errors.append(("passwd", "Passwords don't match."))
        return False
    
    validate_memory()
    validate_cpu()
    validate_cpu_limit()
    validate_disk()
    validate_ip()
    validate_nameserver()
    validate_password()
    
    return errors

def read_default_ovf_settings():
    """ Reads default ovf configuration from file, returns a dictionary of settings."""
    return dict(openvz_config.clist("ovf"))

def read_ovf_settings(ovf_file):
    """ Reads given ovf template configuration file, returns a dictionary of settings."""
    settings = {}
    
    settings["template_name"] = os.path.split(ovf_file.path)[1][:-4]  
    
    vm_type = ovf_file.document.getElementsByTagName("vssd:VirtualSystemType")[0].firstChild.nodeValue
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
    """ Checks if minimum required resources exceed maximum available resources. """
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
