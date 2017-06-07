#!/bin/sh

# Cycle red white and blue though the panels


RWB=(FF0000 707070 0000FF)

while true; do  


		# Scan though all active DHCP leases and send a GREEN screen to each
		# Then wiat a second and send a red bradcast. Repeat

		# ':' is the delimiter here, and there are three fields on each line in the file
		# IFS set below is restricted to the context of `read`, it doesn't affect any other code
		while IFS=' ' read -r when mac ip hostname; do
		  # process the fields
		  # if the line has less than three fields, the missing fields will be set to to an empty string
		  # if the line has more than three fields, `field3` will get the all the values, including the third field, including the delimiter(s)

 	          color=$((RANDOM % 3 ))

		  colorstr=${RWB[ $color ] }

		  echo "Color $colorstr to ip $ip..."

     		  ./udpopc "$ip" "$colostr" 0 59 0 25

	   #   wipe 192.168.174.255 $color

		done < leases.lnk

#		sleep 1

		# braodscast off to all

# 		./udpopc 192.168.174.255 000030 0 59 0 25

		sleep 1

done
