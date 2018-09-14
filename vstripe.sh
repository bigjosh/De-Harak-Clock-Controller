#!/bin/bash

# Cycle though colors, sending lighting each digit in sequence and then clearing the board


#step though some nice colors



while true; do  

	for color in "3f0000" "003f00" "00003f"; do



		for col in {0..59}; do


                ./udpopc 192.168.174.255 $color 0 59 0 25 $col

          sleep 0.25                           

		done 



	done



done
