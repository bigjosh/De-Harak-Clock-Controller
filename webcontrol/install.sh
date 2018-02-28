#!/bin/bash
sudo cp -R var_www/* /var/www/html
sudo chmod +x usr_lib_cgi-bin
sudo cp usr_lib_cgi-bin/* /usr/lib/cgi-bin
sudo systemctl restart apache2

