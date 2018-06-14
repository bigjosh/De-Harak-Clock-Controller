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

    timeout 0.1 ping -c 1 $name   >/dev/null 2>/dev/null
    
    result=$?

    case $result in

        0)
        
            printf " "
        ;;

        1)
            printf "P"
        ;;

        2)    
            printf "N"
        ;;

        *)    ## special value returned by timeout command
            printf "X"
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
       
        #echo 
        #echo "timeout 0.1 ping -c 1 $name"
        #echo


        timeout 0.1 ping -c 1 $name  >/dev/null 2>/dev/null
        
        result=$?
        
        #echo result is $result

        case $result in
        
            0)      
            printf " "
            ;;

            1)
            printf "P"
            ;;

            2)    
            printf "N"
            ;;
            
            *)    ## special value returned by timeout command
            printf "X"
            ;;

        esac

    done
    
    printf "\n"
        
done

