#!/bin/env python

import libvirt
from uuid import UUID
import csv

from opennode.cli.actions.utils import execute2, execute
from opennode.cli.actions.vm import openvz, list_vms
from opennode.cli.actions.vm import vm_interfaces

def get_uuid(vm):
        return str(UUID(bytes=vm.UUID()))

def dump_info(vms, csv):
        """Dump information about VMs of a certain hypervisor into a CSV file"""
        for vm in vms:
                ips = vm['interfaces']
                if len(ips) > 0
                    ip = ips[0].get('ipv4_address', ips[0]['mac'])
                else:
                    ip = 'missing'
                hn = execute('hostname')
                # uptime in h
                uptime_period = 60 * 60.0
                name = vm['name']
                mem = vm['memory'] / 1024.0
                disk = vm['diskspace']['/'] / 1024.0
                vcpus = vm['vcpu']
                uptime = vm['uptime'] if vm['uptime'] else 0
                uptime /= uptime_period
                print name, mem, disk, vcpus, uptime, ip, hn
                csv.writerow([name, mem, disk, vcpus, uptime, ip, hn])

if __name__ == '__main__':
        openvz_vms = list_vms('openvz:///system')
        kvm_vms = list_vms('qemu:///system')
        with open('usage_report.csv', 'wb') as csvfile:
                csvwriter = csv.writer(csvfile, delimiter=';',
                                    quotechar='"', quoting=csv.QUOTE_MINIMAL)
                csvwriter.writerow(['Name', 'Memory', 'Disk', 'Cores', 'Uptime', 'IP info', 'HN'])
                dump_info(openvz_vms, csvwriter)

