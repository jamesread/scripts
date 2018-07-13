#!/bin/bash

ansible-playbook -i OSEv3-inventory -f 20 /usr/share/ansible/openshift-ansible/playbooks/byo/openshift-preflight/check.yml
