#!/bin/sh
# This is called by the dnsmasq server anytime a lease is added or deleted. 
# the dhcp-script param in /etc/dnsmasq.conf should point here

# dnsmasq also has a hook to call a script dhcp-script=foo.sh. 
# The arguments sent to the script are add or del, then the MAC address, the IP address and finally the hostname.

if grep $2 -q /var/clockdhcp/seen.txt; then
	echo "already on the list"
else
	# save MAC and hostname
	echo $(date +%Y%m%d-%H%M%S) "$2" "$3" "$4"   >> /var/clockdhcp/seen.txt
fi
