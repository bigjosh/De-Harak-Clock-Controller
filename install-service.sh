echo Making leds executible...
make leds

echo Setting script file permisions...
chmod +x startledsd.sh

echo Copying LEDscape config file...
cp ledscape-config.json /etc/
echo Restarting LEDscape...
systemctl restart ledscape.service

echo "Enabling ledsd Service..."
systemctl enable $(pwd)/ledsd.service || exit -1

echo "Starting ledsd Service..."
systemctl start ledsd.service
systemctl status ledsd.service

