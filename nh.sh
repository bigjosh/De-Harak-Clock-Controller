#!/bin/sh
#kill previously running copy

if [ -e "/tmp/nh.pid" ]; then
    sudo kill $(cat /tmp/nh.pid)
fi

#run new script with nohup
nohup ./$1 >/dev/null </dev/null  2>stderr.txt &
echo $! >/tmp/nh.pid

