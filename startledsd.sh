#!/bin/sh
DIRNAME="`dirname "$0"`"
cd "$DIRNAME"

echo "delay"
sleep 5
echo starting 

/root/DigitPanelDemo/leds F000f00
