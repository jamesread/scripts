cdrom
install
lang en_GB.UTF8
firewall --service ssh
network --onboot yes --bootproto dhcp
timezone Europe/London
selinux --enforcing
skipx
text
clearpart --all
zerombr
part / --fstype=ext4 --size 8000 --asprimary
bootloader --location=mbr --timeout 10

%packages --ignoremissing
vim-enhanced
git
wget
%end

%post
echo "\nPS1=\"$(tput setaf 1)\u@\h: $(tput setaf 7)\"" >> /root/.bashrc
%end
