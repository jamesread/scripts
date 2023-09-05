#!/bin/bash

for vm in `libvirt-list-vms` ; do virsh shutdown $vm ; done
