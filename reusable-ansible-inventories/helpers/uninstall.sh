#!/bin/bash

ansible-playbook -vv -i OSEv3-inventory -f 20 /usr/share/ansible/openshift-ansible/playbooks/adhoc/uninstall.yml
