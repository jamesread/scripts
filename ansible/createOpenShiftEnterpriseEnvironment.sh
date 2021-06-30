#!/bin/bash

./create.yml -e baseImageFilename=rhel-server-7.5-x86_64-kvm.qcow2 -erh_username="jread@redhat.com" -erh_password="$RH_PASSWORD" -ecount=3 -eramMb=8192 -evmTitle=master
./create.yml -e baseImageFilename=rhel-server-7.5-x86_64-kvm.qcow2 -erh_username="jread@redhat.com" -erh_password="$RH_PASSWORD" -ecount=3 -eramMb=8192 -evmTitle=infra
./create.yml -e baseImageFilename=rhel-server-7.5-x86_64-kvm.qcow2 -erh_username="jread@redhat.com" -erh_password="$RH_PASSWORD" -ecount=3 -eramMb=16384 -evmTitle=app
./create.yml -e baseImageFilename=rhel-server-7.5-x86_64-kvm.qcow2 -erh_username="jread@redhat.com" -erh_password="$RH_PASSWORD" -ecount=1 -eramMb=8192 -evmTitle=applb
./create.yml -e baseImageFilename=rhel-server-7.5-x86_64-kvm.qcow2 -erh_username="jread@redhat.com" -erh_password="$RH_PASSWORD" -ecount=1 -eramMb=8192 -evmTitle=masterlb
