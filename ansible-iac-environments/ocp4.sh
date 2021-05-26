#!/bin/bash

PB_DIR=./../ansible-playbooks/vmcreator-libvirt/

$PB_DIR/create.yml -e rawDisk=100 -e diskSize=100 -e count=3 -e ramMb=16384 -e vmTitle=worker -e vmCustomize=skip -e baseImageFilename=skip
$PB_DIR/create.yml -e rawDisk=100 -e diskSize=100 -e count=3 -e ramMb=16384 -e vmTitle=master -e vmCustomize=skip -e baseImageFilename=skip
$PB_DIR/create.yml -e baseImageFilename=CentOS-8-GenericCloud-8.1.1911-20200113.3.x86_64.qcow2 -e count=1 -e ramMb=4096 -e vmTitle=ocp4-cradle
$PB_DIR/create.yml -e baseImageFilename=CentOS-8-GenericCloud-8.1.1911-20200113.3.x86_64.qcow2 -e count=1 -e ramMb=1024 -e vmTitle=ocp4-dns
$PB_DIR/create.yml -e baseImageFilename=CentOS-8-GenericCloud-8.1.1911-20200113.3.x86_64.qcow2 -e count=1 -e ramMb=2048 -e vmTitle=ocp4-lb
$PB_DIR/create.yml -e baseImageFilename=CentOS-8-GenericCloud-8.1.1911-20200113.3.x86_64.qcow2 -e count=1 -e ramMb=1024 -e vmTitle=bastion
