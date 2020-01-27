#!/bin/bash

PB_DIR=./../ansible-playbooks/vmcreator-libvirt/

$PB_DIR/create.yml -e rawDisk=30 -e count=5 -e ramMb=8192 -e vmTitle=worker -e vmCustomize=skip -e baseImageFilename=skip
$PB_DIR/create.yml -e rawDisk=30 -e count=3 -e ramMb=16384 -e vmTitle=master -e vmCustomize=skip -e baseImageFilename=skip
$PB_DIR/create.yml -e baseImageFilename=CentOS-7-x86_64-GenericCloud.qcow2 -e count=1 -e ramMb=8192 -e vmTitle=ocp4-cradle
$PB_DIR/create.yml -e baseImageFilename=CentOS-7-x86_64-GenericCloud.qcow2 -e count=1 -e ramMb=8192 -e vmTitle=ocp4-dns
