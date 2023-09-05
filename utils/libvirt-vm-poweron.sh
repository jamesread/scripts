#!/bin/bash

for vm in `libvirt-list-vms` ; do virsh start $vm ; done
