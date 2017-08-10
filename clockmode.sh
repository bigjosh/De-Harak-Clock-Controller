#!/bin/bash
# This is the actual clock! Put the digits up every second. Make sure local clock has right time.

color_red=700000
color_blue=000070
color_white=555555
color_bg=100b00 

echo Setting up IP address arrays....

#IP addresses for top panel
top_addr=()

for h in {1..12}; do

	top_addr[h]=$( getent hosts $(printf "h%02d" $h) | awk '{ print $1 }')
done

#IP ddresses for bottom panel
bot_addr=()
for m in {0..59}; do

	bot_addr[m]=$( getent hosts $(printf "m%02d" $m) | awk '{ print $1 }')

done


#set the color of a digit in the minutes section
#param 1=digit number 0-59
#param 2=minutes
#param 3=seconds
#we deal with IP address so we don't have to precompute

# note that when seconds and minutes collide, seconds win

function botsetcolor()
{

    case $1 in
    
        $3)                         # digit is seconds
            color=$color_white             
            ;;
        $2)                         # digit is minutes
            color=$color_blue
            ;;
        *)
            color=$color_bg
            ;;
    esac

    ./udpopc $1 $color 0 59 0 25 >/dev/null
    #echo "M $1 $2 $3 " "./udpopc $1 $color 0 59 0 25"
}


#param 1 =digit
#param 2= hour 
#we deal with IP address so we don't have to precompute

function hsetcolor()
{

   case $1 in

        $2)
            color=$color_red
            ;;
        *)
            color=$color_bg
            ;;
    esac
    
    ./udpopc $1 $color 0 59 0 25 >/dev/null
    #echo "H" $1 $2 " ./udpopc $1 $color 0 59 0 25"

}



# keep track of previous second so we can turn it off quickly for a smoother transision.
# fist time just send back to ourselves since we don't have a previous
# there is no "black hole" IP address in IP4

h_prev_ip=127.0.0.1
m_prev_ip=127.0.0.1
s_prev_ip=127.0.0.1

echo starting to clock!

while true; do  

    # Get hour in current time zone 12 hour format 
    # note that you must use the format versions with a leading 0 or else it will be interpreted as 
    # octal! Yikes!
    
    h=`TZ=":America/New_York" date +%-I`
    m=`date +%-M`
    s=`date +%-S`    

    #fetch IP addresses for relevant digits
    h_ip=${top_addr[$h]}
    m_ip=${bot_addr[$m]}
    s_ip=${bot_addr[$s]}
    
    # For testing, speed up hours so we can check all digits    
    # comment next two lines for normal operations
    #h_fast=$(( ($s % 12) + 1))
    #h_ip=${top_addr[$h_fast]}
    
    
	# fist do a quick update to get changed digits lit up correctly
    
    #hour panel easy because no collisions
           
    
    #hour
    
    hsetcolor $h_ip  $h_ip        
        
    #erase prev hour only if changed, otherwise it will just blink briefly
              
    if [ "$h_prev_ip" != "$hip" ]; then    
        hsetcolor $h_prev_ip  $h_ip        
    fi
    
       
    #quickly update the digits that could have changed in the minute panel

    botsetcolor $s_ip       $m_ip   $s_ip       #update s
    botsetcolor $s_prev_ip  $m_ip   $s_ip       #off previous s

    botsetcolor $m_ip       $m_ip   $s_ip       #update m
    botsetcolor $m_prev_ip  $m_ip   $s_ip       #off previous m

    
    #save for next pass
    s_prev_ip=$s_ip
    m_prev_ip=$m_ip
    h_prev_ip=$h_ip

    
	# next do a refresh just to keep off digits from going into demo mode 
	# and clean up any missed UDP packets
    
    # break refresh into two phases - top and bottom - becuase 
    # every once and a while we do not have time to do everythgin in 
    # less than one second maybe becuase of system load

    scan_phase=$(( $s % 2 ))

    blink_phase=$(( $s % 4 ))
        
 
    
    
    if [ "$scan_phase" = "0" ]; then
    
        for scan_ip in "${bot_addr[@]}"; do
                
            botsetcolor $scan_ip   $m_ip   $s_ip 
        
        done
        
    else

        #...and hours....
        
        for scan_ip in "${top_addr[@]}"; do
            
            hsetcolor $scan_ip   $h_ip

        done
        
    fi    
    
    # update the background to be yellow at night to match the 
    # old incadecent backlights
    # no point in showing durring the day becuase not visible, so save    
    # a bit of power and wear and tear by onlt turning on
    # when pople are likely to see it
    
    h24=`TZ=":America/New_York" date +%k`
    
    # off btween 3AM and 8PM
        
    if (( $h24 > 3 )) && (( $h24 < 20 )); then     
        color_bg=000000
    else
        color_bg=100c00                 
    fi
    
    case $blink_phase in

        0)
            color_bg=100b00
            ;;
        1)
            color_bg=100000
            ;;
        2)
            color_bg=001000
            ;;
        3)
            color_bg=000010
            ;;
            
    esac   
                
           
    # sleep until next round second
    # https://stackoverflow.com/a/33226295/3152071
        
    sleep 0.$(printf '%04d' $((10000 - 10#$(date +%4N))))    
     
 done

<br>
<a href="https://youtu.be/8rMb_84f0gw">https://youtu.be/8rMb_84f0gw</a>
<br>

