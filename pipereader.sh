#!/bin/bash
#read from a named pipe to get commands

pipe=/tmp/clockcommands

trap "rm -f $pipe" EXIT


if [[ ! -p $pipe ]]; then
    mkfifo $pipe
fi


#let everyone use it
chmod a+rw $pipe


while true
do
    if read line <$pipe; then
    
        echo "pipereader "
        
        echo "pip:" $line  >>/tmp/clockcommands.log
  
        case "$line" in
            "ticktest"*) 
                 echo "Got ticktest" 
                 ./nh.sh ./ticktest.sh
                 ;;
                 
            "clockmode"*) 
                 echo "Got clockmode" 
                 ./nh.sh ./clockmode.sh                 
                 ;;
                 
                 
            *)
                echo "Unknown request"
                ;;
            
        esac
               
        
    fi
done

echo "Reader exiting"
