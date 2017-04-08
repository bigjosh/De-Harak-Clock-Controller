echo Making leds executable...
make

echo making dir in /var

sudo mkdir /var/clockdhcp

echo Moving dhcp script to /usr/local

sudo cp dhcp-script.sh /usr/local

echo ...and making it executable

sudo chmod +x /usr/local/dhcp-script.sh

#echo Making service install script executable...
#chmod +x install-service.sh
#echo Run install-service.sh to make ledsd start on boot...
