#!/bin/sh

# Run a command on each host in the seen file
#

# ':' is the delimiter here, and there are three fields on each line in the file
# IFS set below is restricted to the context of `read`, it doesn't affect any other code
while IFS=' ' read -r when mac ip hostname; do
  # process the fields
  # if the line has less than three fields, the missing fields will be set to to an empty string
  # if the line has more than three fields, `field3` will get the all the values, including the third field, including the delimiter(s)

  sshpass -p temppwd ssh "debian@$ip" -oStrictHostKeyChecking=no "sudo killall leds"

  # echo "$when" "$ip"
done < seen.lnk

