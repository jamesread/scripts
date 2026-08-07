#!/usr/bin/bash

cd

curl -O http://www.jread.com/scripts/profile.txt 
mv profile.txt .bashrc
source ~/.bashrc
profile_box_bootstrap
profile_git_clone_scripts

cat <<EOT >> /etc/ansible/hosts
[common]
localhost
EOT

profile_ansible_apply_local
