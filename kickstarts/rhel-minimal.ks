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
part /boot
part swap --recommended
part pv.1 --size 1024 --grow
volgroup vg_root pv.1
logvol / --size 1024 --grow --name lv_root --vgname vg_root
bootloader --location=mbr --timeout 10
reboot

%packages --ignoremissing
vim-enhanced
git
wget
%end

%post
wget http://www.jwread.com/var/nix/profile.txt -O /root/.bashrc
%end
