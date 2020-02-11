#!/bin/bash
# This is the actual clock! Put the digits up every second. Make sure local clock has right time.

color_red="800000"
color_blue="000070"
color_white="303030"
color_green="0060070"

color_bg_day="000000"
color_bg_night="202020"

bcastip="192.168.174.255"

#clear board
./udpopc  $bcastip 000000 0 59 0 25 >/dev/null


echo Setting up IP address arrays....

#IP addresses for top panel
top_addr=()

for h in {1..12}; do

    if addr=$(getent hosts $(printf "h%02d" $h)); then 
        
        top_addr[h]=$(echo $addr | awk '{ print $1 }')        
        ./udpopc  ${top_addr[h]} 008000 0 59 0 25 >/dev/null
        
    else
    
        echo No DNS found for $(printf "h%02d" $h)
        top_addr[h]="127.0.0.1"
        
    fi 
done


#IP ddresses for bottom panel
bot_addr=()
for m in {0..59}; do


    if addr=$(getent hosts $(printf "m%02d" $m)); then 
        
        bot_addr[m]=$(echo $addr | awk '{ print $1 }')
        ./udpopc  ${bot_addr[m]} 008000 0 59 0 25 >/dev/null
        
    else 
    
        echo No DNS found for $(printf "m%02d" $m)
        bot_addr[m]="127.0.0.1"
        
    fi 


done

./udpopc  $bcastip 000000 0 59 0 25 >/dev/null


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
            color=$color_green             
            ;;
        $2)                         # digit is minutes
            color=$color_blue
            ;;
        *)
            color=$color_bg
            ;;
    esac

    ./udpopc $1 $color 0 59 0 25 >/dev/null
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

    h24=`TZ=":America/New_York" date +%k`

    h=$(( $h24 % 12 )) 
    m=`date +%-M`
    s=`date +%-S`    

    # clocks dont start at 0

    if (( "$h" == "0" )); then
        h=12
    fi

    # These tests are temporary to skip over digit m01 which
    # is not working right now. 

    if (( "$m" == "1" )); then
        m=1
    fi

    if (( "$s" == "1" )); then
        s=1
    fi



    # determine background color for this pass

    # update the background to be yellow at night to match the 
    # old incadecent backlights
    # no point in showing durring the day becuase not visible, so save    
    # a bit of power and wear and tear by onlt turning on
    # when pople are likely to see it
    
    
    # off btween 3AM and 8PM
        
    if (( $h24 > 4 )) && (( $h24 < 18 )); then     
        color_bg=$color_bg_day
    else
        color_bg=$color_bg_night
    fi
 
                
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

    
    if [ "$scan_phase" = "0" ]; then

        #...top digits...
        
        for scan_ip in "${top_addr[@]}"; do
            
            hsetcolor $scan_ip   $h_ip

        done 

    else 

        #...bottom digits....
    
        for scan_ip in "${bot_addr[@]}"; do
                
            botsetcolor $scan_ip   $m_ip   $s_ip 
        
        done
        
    fi    
    
           
    # sleep until next round second
        
    ./nextsecond

done
