#!/usr/bin/env bash

# show status of all digits in a line suitable for logging

# line starts with time followed by one letter per digit in order
# .=Good,P=ping ailed, H=Host lookup failed

# timestamp

##printf $(date "+%4y%2m%2d %2H%2M ")
printf $(date "+%k%M ")

# top row...


for h in {1..12}; do

    if addr=$(getent hosts $(printf "h%02d" $h)); then 
        
        ip=$(echo $addr | awk '{ print $1 }')        
        
        if ping -c 1 $ip >/dev/null; then         
            printf "."
        else
            printf "P"
        fi
    else
    
        printf "H"
        
    fi 
done


# bottom rows...

for r in {0..4}; do 

    for c in {0..11}; do 

        m=$(((r*12)+c))


        if addr=$(getent hosts $(printf "m%02d" $m)); then 
            
            ip=$(echo $addr | awk '{ print $1 }')        
            
            if ping -c 1 $ip >/dev/null; then         
                printf "."
            else
                printf "P"
            fi
        else
        
            printf "H"
            
        fi 
    done
    
        
done

printf "\n"
