#!/bin/sh
#kill previously running copy
sudo kill $(cat /tmp/nh.pid)

#run new script with nohup
nohup ./$1 >/dev/null &
echo $! >/tmp/nh.pid

