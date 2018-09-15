The controller present a web interface using apache and CGI script.

The static web stuff lives in `/webcontrol` and gets copied into the correct directories used by appache using the `install.sh` script. You should run this script anytime you update any of the web files.

The back end cgi scripts talk to the controller using a named pipe called `/tmp/clockcommands`. `light.cgi` writes to the pipe and `pipereader.sh` reads from it. 

To enable the web-based clock controls...

1. Install apache...

```
sudo apt-get install apache2 -y
```

2. Enable cgi...

```
a2enmod cgi
```

3. Restart server

```
sudo service apache2 restart
```

Now run the `webcontrol/install.sh` script to put any cgi files in `/usr/lib/cgi-bin` and `chmod +x` them. 
