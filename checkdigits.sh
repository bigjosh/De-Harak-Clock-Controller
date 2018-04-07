# show status of all digits visually
# using DNS and ping


echo "N means host not found in DNS"
echo  "T means  ping timeout"
echo "- means good ping"

# top row...

for h in {1..12}; do

	name=$(printf "h%02d" $h)

 	#echo name $name

	printf " $name"

        timeout 0.3 ping -c 1 $name   >/dev/null 2>/dev/null

        case $? in

            0)
		
	    	printf " "
		;;

	    1)
         	printf "P"
		;;

            2)    
       		printf "N"
		;;

            124)    ## special value returned by timeout command
       		printf "T"
		;;
	esac

done

printf "\n"

# bottom rows...

for r in {0..4}; do 

    for c in {0..11}; do 

        m=$(((r*12)+c))

        name=$(printf "m%02d" $m)

	printf " $name"

        #echo name $name

        timeout 0.3 ping -c 1 $name   >/dev/null 2>/dev/null

        case $? in

            0)
		
	    	printf " "
		;;

	    1)
         	printf "P"
		;;

            2)    
       		printf "N"
		;;
            124)    ## special value returned by timeout command
       		printf "T"
		;;

	esac

    done
    
    printf "\n"
        
done

