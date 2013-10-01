#!/bin/bash

domain=$1
device=$2

virsh domblkinfo $domain $device |grep ^Capacity| awk '{print $2}'

