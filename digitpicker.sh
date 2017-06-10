# This utility lets you assign names to digits on the clock
# You see a list of MAC addresses representing all the nodes on the network
# Pick a line and push enter and what the clock to see which digit blinks. 
# Then enter the name of that digit in the form M00 or H00
# so M11 is the top 11 and H48 is the bottom(only) 48
# If no digit blinks or it is the already assigned one, press enter
#
# Press save when done to write the entires to the dhcphosts file
# dhcp-hostsfile = /etc/dhcp-hostsfile.conf

i=0

#read leases file line by line and make menu
while read p
do

#	echo "Line=$p"

    read -ra arr <<<"$p"

#	echo "0=${arr[0]} 1=${arr[1]}"


	# MAC first
    list[i]=${arr[1]}

	# DNS Name second
    list[i+1]=${arr[3]}
    ((i+=2))
done <leases.txt

# all active machines now loaded in arr

finished=false

#start with first item selected
current=${list[0]}

while [ "$finished" = false ] ; do

	mac=$(
		whiptail --default-item "$current" --menu "Pick an address" --ok-button "Blink (enter)" --cancel-button "Save (esc)" 24 70 18 "${list[@]}" 3>&2 2>&1 1>&3
	)

	response=$?

	if [ $response -eq 0 ]; then

		echo $mac
		read

		current=$mac


	else

		echo Finsihed
		read

		finished=true

	fi


done

# restart dhcp server so it reads new assignments
# service dhcpd restart