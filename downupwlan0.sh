#!/bin/sh
# called 1am from crontab
# so sad we have to do this, but wlan dies freqently and never comes back
ifdown wlan0
ifup wlan0

