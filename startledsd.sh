#!/bin/sh
DIRNAME="`dirname "$0"`"
cd "$DIRNAME"

echo "delay"
sleep 5
echo starting 

/root/DigitPanelDemo/leds P000f00
