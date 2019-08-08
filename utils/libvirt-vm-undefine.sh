#!/bin/bash

echo "########"
echo "######## Undefine and delete everything?! Are you SURE?! :-)"
echo "########"
read 

for vm in `./list-libvirt-vms.sh` ; do virsh snapshot-delete --current --domain $vm; virsh undefine $vm --remove-all-storage ; done
