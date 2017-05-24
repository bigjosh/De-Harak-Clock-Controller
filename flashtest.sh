#!/bin/sh


wipe () {

	for row in $(seq 0 58); do 

		./udpopc "$1" "$2" 0 59 0 25
		# sleep 0.01

	done

   	return 0
}

#stop though some nice colors

while true; do  


	for color in "FF0000" "00FF00" "0000FF"; do

		# Scan though all active DHCP leases and send a GREEN screen to each
		# Then wiat a second and send a red bradcast. Repeat

		# ':' is the delimiter here, and there are three fields on each line in the file
		# IFS set below is restricted to the context of `read`, it doesn't affect any other code
		while IFS=' ' read -r when mac ip hostname; do
		  # process the fields
		  # if the line has less than three fields, the missing fields will be set to to an empty string
		  # if the line has more than three fields, `field3` will get the all the values, including the third field, including the delimiter(s)

		  echo "Color $color to ip $ip..."

	      wipe $ip $color

		done < leases.lnk

		sleep 1

		# braodscast off to all

 		./udpopc 192.168.174.255 000000 0 59 0 25

		sleep 1

	done

done
