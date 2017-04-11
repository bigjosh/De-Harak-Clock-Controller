#!/bin/sh

# Kill the default bullseye demo running on all BBB
#

# ':' is the delimiter here, and there are three fields on each line in the file
# IFS set below is restricted to the context of `read`, it doesn't affect any other code
while IFS=' ' read -r when mac ip hostname; do
  # process the fields
  # if the line has less than three fields, the missing fields will be set to to an empty string
  # if the line has more than three fields, `field3` will get the all the values, including the third field, including the delimiter(s)

  echo "Calling $ip..."
  #sshpass -p temppwd ssh "debian@$ip" ssh -o StrictHostKeyChecking=no root "sudo killall leds"
  #ssh o StrictHostKeyChecking=no root "root@$ip" "sudo killall leds"
 
  # need -n or else breaks loop. Ahhhh!  http://stackoverflow.com/a/1396070/3152071
  #ssh -n -o StrictHostKeyChecking=no "root@$ip" "sudo killall leds"

  if ! grep "$mac" ledsdis.txt; then 
     if ssh -n -o StrictHostKeyChecking=no "root@$ip" "systemctl disable /root/DigitPanelDemo/ledsd.service"; then

   	echo success
	echo $mac >>ledsdis.txt
    else 
	echo failed $?

    fi

  else 

    echo "already found $mac"

  fi

  
	
  # echo "$when" "$ip"

done < leases.lnk
