
#!/bin/bash

for vm in `./list-libvirt-vms.sh` ; do virsh destroy $vm ; done
