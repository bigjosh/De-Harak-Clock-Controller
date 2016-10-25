echo Copying config file...
cp ledscape-config.json /etc/

echo "Enabling Service..."
systemctl enable $(pwd)/ledsd.service || exit -1

echo "Starting Service..."
systemctl start ledsd.service
systemctl status ledsd.service

