#!/bin/sh

## Read the list of ranbow cycle colors from sinebowcycle.txt
## and broadcast to all digits

while true; do  


		while IFS=' ' read -r color; do

			# braodscast off to all
	 	 	./udpopc 192.168.174.255 $color 0 59 0 25

		
			sleep 0.1
	

		done < sinebowcycle.txt


	done

done
