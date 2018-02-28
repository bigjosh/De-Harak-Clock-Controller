#!/bin/bash
#read from a named pipe to get commands

echo first find the install directory

#https://gist.github.com/TheMengzor/968e5ea87e99d9c41782
SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do # resolve $SOURCE until the file is no longer a symlink
  DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"
  SOURCE="$(readlink "$SOURCE")"
  [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE" # if $SOURCE was a relative symlink, we need to resolve it relative to the path where the symlink file was located
done
DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"

#now switch to the install directory (we might be running from a link in /usr/bin/local)

cd "$DIR"

echo "in dir:" $PWD  

echo Starting pipereader

pipe=/tmp/clockcommands

trap "rm -f $pipe" EXIT


if [[ ! -p $pipe ]]; then
    mkfifo $pipe
fi


#let everyone use it
chmod a+rw $pipe

ehco Starting clock mode
./clockmode.sh &

while true
do
    if read line <$pipe; then
            
        echo "pip:" $line 
  
        case "$line" in
            "ticktest"*) 
                 echo "Got ticktest" 
                 # kill any running child process
                 pkill -P $$
                 ./ticktest.sh &
                 ;;
                 
            "clockmode"*) 
                 echo "Got clockmode" 
                 # kill any running child process
                 pkill -P $$                 
                 ./clockmode.sh &
                 ;;
                 
                 
            *)
                echo "Unknown request"
                ;;
            
        esac
               
        
    fi
done

echo "Reader exiting"
