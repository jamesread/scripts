RULE=`cat ../examples/nics.rules`
MACS=`ip link show | awk '/ether/ {print $2}'`

for mac in $MACS; do
	sed "s/00:00:00:00:00:00/$mac/g" ../examples/nics.rules >> /etc/udev/rules.d/jwr.rules
done

