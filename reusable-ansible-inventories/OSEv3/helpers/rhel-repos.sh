ansible -m shell -a 'subscription-manager repos --disable="*"    --enable="rhel-7-server-rpms"     --enable="rhel-7-server-extras-rpms"     --enable="rhel-7-fast-datapath-rpms"     --enable="rhel-7-server-ansible-2.4-rpms"     --enable="rhel-7-server-ose-3.10-rpms"' -i OSEv3-inventory all

subscription-manager repos --disable="*"    --enable="rhel-7-server-rpms"     --enable="rhel-7-server-extras-rpms"     --enable="rhel-7-fast-datapath-rpms"     --enable="rhel-7-server-ansible-2.4-rpms"     --enable="rhel-7-server-ose-3.10-rpms"
