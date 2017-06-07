#!/bin/sh

# Cycle slow red white and blue though the panels using a master broadcast 

#pulse pulses a color. pass address and color mask

pulsec () {

	for i in $(seq 1 7 200); do 


		./udpopc "$1" `printf $2 $i` 0 59 0 25
		sleep 0.1
	done

	for i in $(seq 200 -7 0); do 

		./udpopc "$1" `printf $2 $i` 0 59 0 25
		sleep 0.1

	done
}

pulsew () {

	for i in $(seq 1 7 200); do 

		./udpopc "$1" `printf %02X%02X%02X  $i $i $i` 0 59 0 25
		sleep 0.1
	done

	for i in $(seq 200 -7 0); do 


		./udpopc "$1" `printf %02X%02X%02X  $i $i $i` 0 59 0 25


		sleep 0.1

	done
}





while true; do  

	pulsec 192.168.174.255 "%02X0000"

	sleep 1

	pulsew 192.168.174.255 "%02X0000"

	sleep 1

	pulsec 192.168.174.255 "0000%02X"

	sleep 2


done
