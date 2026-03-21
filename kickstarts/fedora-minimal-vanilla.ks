cdrom
install
reboot
rootpw password
lang en_GB.UTF8
firewall --service ssh
network --onboot yes --bootproto dhcp --ipv6 off
timezone Europe/London
selinux --enforcing
skipx
text
clearpart --all
zerombr
part /boot --size 1024
part pv1 --grow
part swap --recommended
volgroup vg_root pv1
logvol / --fstype=xfs --grow --name lv_root --vgname vg_root
bootloader --location=mbr --timeout 10

%packages --ignoremissing
vim-enhanced
git
wget
%end

%post
yum update -y --skip-broken
%end
