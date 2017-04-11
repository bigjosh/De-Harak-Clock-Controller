#!/bin/sh

# Scan though all active DHCP leases and send a GREEN screen to each
# Then wiat a second and send a red bradcast. Repeat

while true; do  

	# ':' is the delimiter here, and there are three fields on each line in the file
	# IFS set below is restricted to the context of `read`, it doesn't affect any other code
	while IFS=' ' read -r when mac ip hostname; do
	  # process the fields
	  # if the line has less than three fields, the missing fields will be set to to an empty string
	  # if the line has more than three fields, `field3` will get the all the values, including the third field, including the delimiter(s)

	  echo "Green to  $ip..."

	  ./udpopc $ip 008000 0 59 0 24
	  sleep 0.02

	done < leases.lnk

	sleep 2

	# braodscast blue to all

 	./udpopc 192.168.174.255 000080 0 59 0 24

	sleep 1

done
