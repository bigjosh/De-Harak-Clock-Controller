#!/bin/sh
# called 1am from crontab
# so sad we have to do this, but wlan dies freqently and never comes back
sudo ifdown wlan0
sudo ifup wlan0

