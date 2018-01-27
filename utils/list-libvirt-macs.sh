#!/bin/bash

for vm in `./list-libvirt-vms.sh`; do echo $vm; virsh domiflist $vm | tail -n +3 | awk '{print $5}'; done
