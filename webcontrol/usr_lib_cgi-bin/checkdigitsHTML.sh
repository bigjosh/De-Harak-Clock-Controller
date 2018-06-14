# show status of all digits visually
# using DNS and ping


echo "<div bgcolor=#F5B7B1>N</div> means host not found in DNS<br>"
echo "<div bgcolor=#F5B7B1>P</div> means  ping timeout<br>"

# showcell takes h or m as first arg, then number as Second arg

function showcell() {
	name=$(printf "$1%02d" $2)    
	printf "<td bgcolor=$4>$name $3</td>"    
}

echo "<h2>Running ping test, will take a second...</h2><br>"

echo "<table width=100% border=1 cellspacing=2 cellpadding=2>"

# top row...

echo "<tr>"

for h in {1..12}; do

	name=$(printf "h%02d" $h)

 	#echo name $name


    timeout 0.3 ping -c 1 $name   >/dev/null 2>/dev/null

    case $? in

        0)
    
            showcell "h"  $h  " "  "#82E0AA"
            ;;

        1)
            showcell "h"  $h  "P"  "#F5B7B1"        
            ;;

        2)    
            showcell "h"  $h  "N"  "#F5B7B1"
            ;;

        124)    ## special value returned by timeout command
            showcell "h"  $h  "T"  "#F5B7B1"
            ;;
	esac

done

echo "</tr><tr>"


# bottom rows...

for r in {0..4}; do 

    for c in {0..11}; do 

        m=$(((r*12)+c))


        #echo name $name

        timeout 0.3 ping -c 1 $name   >/dev/null 2>/dev/null

        case $? in

            0)
        
                showcell "m"  $m  " "  "#82E0AA"
                ;;

            1)
                showcell "m"  $m  "P"  "#F5B7B1"        
                ;;

            2)    
                showcell "m"  $m  "N"  "#F5B7B1"
                ;;

            124)    ## special value returned by timeout command
                showcell "m"  $m  "T"  "#F5B7B1"
                ;;
        esac

    done
    
    echo "</tr><tr>"
        
done

echo "</tr></table>"

