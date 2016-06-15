echo "Enabling ledsd Service..."
systemctl enable $(pwd)/ledsd.service || exit -1

echo "Starting ledsd Service..."
systemctl start ledsd.service
systemctl status ledsd.service

