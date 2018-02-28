echo This should be in the directory called /home/pi/clock-controller

echo Making leds executable...
make

echo making dir in /var

sudo mkdir /var/clockdhcp

echo Moving dhcp script to /usr/local

sudo cp dhcp-script.sh /usr/local

echo ...and making it executable

sudo chmod +x /usr/local/dhcp-script.sh

echo restartig dnsmasq to use new config settings...

sudo systemctl restart dnsmasq.service

#echo Making service install script executable...
#chmod +x install-service.sh
#echo Run install-service.sh to make ledsd start on boot...

echo Making dir for the digits log 

mkdir /home/pi/logs

echo Now make sure you chontab -e the stuff in the file crontab.txt!
echo Also install apache2 and the webcontroller install.sh if you want remote access!
echo Also install the pipereader service with is used to start effects by the webservice (and others)


