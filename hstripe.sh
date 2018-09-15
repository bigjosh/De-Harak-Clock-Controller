#!/bin/bash



# Cycle though colors, sending light a horazontal stripe that scans across all digits.
# good for finding upsidedown digits and dead rows. 




#step though some nice colors







while true; do  



	for color in "8f0000" "008f00" "00008f"; do






		for row in {0..25}; do





                ./udpopc 192.168.174.255 $color 0 59 0 25 60 $row



          sleep 0.1                           



		done 







	done







done
