# execute a command on ever digit

# this depends on the DNSMASQ being used and configured correctly

#read leases file line by line and make an associative array of mac:name

declare -A names
declare -A addresses

while read p
do

#	echo "Line=$p"

    read -ra arr <<<"$p"

#	echo "0=${arr[0]} 1=${arr[1]}"


	# name is 3rd thing on leases file line (IP is second)
    names[${arr[1]}]="${arr[3]}"

    addresses[${arr[1]}]="${arr[2]}"



done </var/lib/misc/dnsmasq.leases

