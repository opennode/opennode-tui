#!/bin/bash

# libvirt domain
domain=$1
# output is expected to be a list of file-based devices
virsh domblklist --details $domain |  grep ^file | awk '{print $4}'

