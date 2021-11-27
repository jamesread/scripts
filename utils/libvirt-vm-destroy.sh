
#!/bin/bash

for vm in `libvirt-list-vms` ; do virsh destroy $vm ; done
