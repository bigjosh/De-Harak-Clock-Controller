#!/bin/bash

# Cycle though colors, sending lighting each digit in sequence and then clearing the board


#step though some nice colors



while true; do  

	for color in "8f0000" "008f00" "00008f"; do



		for col in {0..58}; do


                ./udpopc 192.168.174.255 $color 0 59 0 25 $col

          sleep 0.1                           

		done 



	done



done
