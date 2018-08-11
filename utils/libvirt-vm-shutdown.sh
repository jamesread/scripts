#!/bin/bash

for vm in `./list-libvirt-vms.sh` ; do virsh shutdown $vm ; done
