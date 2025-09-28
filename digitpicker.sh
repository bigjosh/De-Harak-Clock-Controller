# This utility lets you assign names to digits on the clock
# You see a list of MAC addresses representing all the nodes on the network
# Pick a line and push enter and what the clock to see which digit blinks. 
# Then enter the name of that digit in the form M00 or H00
# so M11 is the top 11 and H48 is the bottom(only) 48
# If no digit blinks or it is the already assigned one, press enter
#
# Press save when done to write the entires to the dhcphosts file
# dhcp-hostsfile = /etc/dhcp-hostsfile.conf
#
# format for that file is mac,name
#
# this depends on the DNSMASQ being used and configured correctly

#read leases file line by line and make an associative array of mac:name


#!/bin/bash

# Declare associative array
declare -A names
declare -A ips
# Declare non-associative array to keep sorted order
declare -a macs

# Sort the file and process each line
while IFS=' ' read -r timestamp mac ip name _; do
    # Skip empty lines
    [ -z "$ip" ] && continue

    # Assign values to arrays

    #macs is a non-associative array so keeps order
    macs+=("$mac")
    names[$mac]="$name"
    ips[$mac]=$ip

done < <(sort -k4 /var/lib/misc/dnsmasq.leases)

# Print the results (optional)

echo -e "MAC:NAME:"
for mac in "${macs[@]}"; do
    echo "$mac: ${names[$mac]}"
done


# all active machines now loaded in arrays

finished=false

#start with first item selected
current=${macs[0]}

while [ "$finished" = false ] ; do

        #build the command line for the menu from the ass array

        i=0

        # loop though keys

        for mac in "${macs[@]}"; do 

            #tag
            menu[i]="$mac"

            #display
            menu[i+1]="${names[$mac]}"
            ((i+=2))

        done

        # DNS Name second

        mac=$(
                whiptail --default-item "$current" --menu "Pick an address" --ok-button "Blink (enter)" --cancel-button "Save" 24 60 18 "${menu[@]}" 3>&2 2>&1 1>&3
        )

        response=$?

        if (( $response == 0 )); then

                        # they picked a line, lets figure out which one

                        address="${ips[$mac]}"

                        #broadcast to turn off all
                        ./udpopc 192.168.174.255 000020 0 59 0 25

                        #blink  selected digit
                        ./udpopc $address 800000 0 59 0 25
                        sleep 0.1

                        ./udpopc $address 008000 0 59 0 25
                        sleep 0.1

                        ./udpopc $address 800000 0 59 0 25
                        sleep 0.1

                        name="${names[$mac]}"

                        newname=$(
                                whiptail --inputbox --ok-button "Ok (enter)" --cancel-button "Cancel (esc)" "New name for $name" 8 40  3>&2 2>&1 1>&3
                        )

                        if [[ ! -z "$newname" ]]; then

                                names[$mac]="$newname"

                        fi

                        current=$mac

        elif (( $response == 1 )); then

                # save 

                echo "Saving to /etc/dhcp-hostsfile.conf..."

                tmpfile=$(mktemp /tmp/digitpicker.XXXXXX)

                # loop though keys and create entries in host file

                for mac in "${macs[@]}"; do 

                        echo "$mac,${names[$mac]}" >>"$tmpfile"

                done

                echo "New Host file created." 

                #overwrite old file

                sudo cp "$tmpfile" /etc/dhcp-hostsfile.conf

                echo "Host file updated." 

                rm "$tmpfile"

                finished=true

        elif (( $response == 255 )); then

                whiptail --yesno "Quit without saving?" 8 40 

                if [ $? -eq 0 ]; then

                        echo "Quiting without saving...."
                        finished=true

                fi

        fi


done

# restart dhcp server so it reads new hostfile
sudo systemctl restart dnsmasq
