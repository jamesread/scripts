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

%packages
vim-enhanced
git
wget
%end

%post
wget http://www.jwread.com/var/nix/profile.txt -O /root/.bashrc
%end
