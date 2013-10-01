#!/bin/bash

domain=$1
device=$2

virsh -c qemu:///system domblkinfo $domain $device |grep ^Capacity| awk '{print $2}'

