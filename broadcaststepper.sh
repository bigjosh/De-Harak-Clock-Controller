#!/bin/sh

# Run alittle stepping pattern on all listing digits
#


while true; do 

        for i in `seq 0 58`;
        do
		./udpopc 192.168.174.255 0000FF 0 $i 0 24
		sleep 0.1
        done    

done	

