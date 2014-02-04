%pre
chvt 3
exec </dev/tty3> /dev/tty3
clear
read -p "What is my FQDN?" NAME /dev/tty3 2>&1
echo "NETWORKING=yes" > network
echo "HOSTNAME=${NAME}" >> network
echo "DEVICE=eth0" > ifcfg-eth0
echo "BOOTPROTO=dhcp" >> ifcfg-eth0
echo "ONBOOT=yes" >> ifcfg-eth0
echo "DHCP_HOSTNAME=${NAME} " >> ifcfg-eth0
cat ifcfg-eth0
chvt 1
exec < /dev/tty1 > /dev/tty1
%end
