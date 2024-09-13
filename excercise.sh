# run a job that simulates real clock life
# use ampersand to run in the background so it does not die if you lose console connection
# use control-z to push to background so you can kill it
while true
do
   timeout 1h ./leds F00FF00
   timeout 15m ./leds F000000
   timeout 1h ./leds F0000FF
   timeout 15m ./leds F000000
   timeout 1s ./leds Fff0000
   timeout 1m ./leds f000000
done
