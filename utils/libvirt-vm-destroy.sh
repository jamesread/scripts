#!/bin/bash

echo "########"
echo "######## DESTROY?! Are you SURE?! :-)"
echo "########"
read 

for vm in `./list-libvirt-vms.sh` ; do virsh snapshot-delete --current --domain $vm; virsh undefine $vm --remove-all-storage ; done
