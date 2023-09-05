#!/bin/bash

for vm in `virsh list --all | tail -n +3 | awk '{print $2}'`; do echo $vm; done
