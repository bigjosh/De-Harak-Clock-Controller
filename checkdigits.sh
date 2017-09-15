# show status of all digits visually
# using DNS and ping


echo "H means host not found in DNS"
echo  "P means failed to ping"
echo

# top row...

for h in {1..12}; do

    if addr=$(getent hosts $(printf "h%02d" $h)); then 
        
        ip=$(echo $addr | awk '{ print $1 }')        
        
        if ping -c 2 $ip >/dev/null; then         
            printf "  h%02d " $h
        else
            printf " Ph%02dP" $h
        fi
    else
    
        printf " Hh%02dH" $h
        
    fi 
done

printf "\n"


# bottom rows...

for r in {0..4}; do 

    for c in {0..11}; do 

        m=$(((r*12)+c))


        if addr=$(getent hosts $(printf "m%02d" $m)); then 
            
            ip=$(echo $addr | awk '{ print $1 }')        
            
            if ping -c 2 $ip >/dev/null; then         
                printf "  m%02d " $m
            else
                printf " Pm%02dP" $m
            fi
        else
        
            printf " Hm%02dH" $m
            
        fi 
    done
    
    printf "\n"
        
done

