#!/bin/sh


wipe () {

	for col in $(seq 0 25); do 

		./udpopc "$1" "$2" 0 59 0 $col
#		./udpopc "$1" "$2" 0 59 0 25
		 sleep 0.02

	done

   	return 0
}

#stop though some nice colors

while true; do  


	for color in "8F0000" "008F00" "00008F"; do

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
	   #   wipe 192.168.174.255 $color

		done < leases.lnk

		sleep 1

		# braodscast off to all

 		./udpopc 192.168.174.255 000030 0 59 0 25

		sleep 1

	done

done
