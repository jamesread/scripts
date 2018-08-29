#!/bin/bash

for vm in `./list-libvirt-vms.sh`; do
	echo $vm;
	
	for mac in `virsh domiflist $vm | tail -n +3 | awk '{print $5}'`; do
		ip=`arp -n | grep "$mac" | awk '{print $1}' `

		echo "    $mac    $ip"
	done

	echo " "
done
