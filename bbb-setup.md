Then flash the LEDscape image on to the Beaglebone by putting an SD card with this image in it...
https://github.com/bigjosh/LEDscape/releases/tag/1.1
...and holding the USR button (near SD slot) at power up until you see cylon LED pattern. 

At power up, the board should go into `redbeat` pattern where it flashes red 1 second per minute. 

To check the LED layout is correct, send something like a bullseye pattern from a controller. 

## If you are on the BBB

```
sudo systemctl disable /root/DigitPanelDemo/ledsd.service
sudo killall leds
```

Steps to make a BBB into a controller if you don't want to use the premade image above, here are steps to create it..

1. Start with installing Debian 7.11 2015-06-15 4GB SD LXDE. http://beagleboard.org/getting-started
2. Install `Ledscape` https://github.com/bigjosh/LEDscape#installation
3. Install `bbbphyfix` https://github.com/bigjosh/bbbphyfix#install
4. Install `devmemkb` https://github.com/bigjosh/devmemkm#installation
5. Remove `wicd`...
    3. `nano /etc/network/interfaces`
    4. Uncomment these two lines...
        1. `auto eth0`
        2. `iface eth0 inet dhcp`
    1. `apt-get remove wicd*`
    2. `apt-get remove wpasupplicant` 
6. Remove other stuffs (the less stuff running, the lower cahnces of the PRU getting interrupted on memory bus accesses)...
   ```
   apt-get remove apache2
   apt-get remove chromium-browser-l10n
   apt-get autoremove
   ```   
6. Install `ledscape-config.json` with (note we need the no-certificate becuase this debian is so old that it does not get cert updates anymore)...
    2. `wget -O /etc/ledscape-config.json --no-check-certificate https://raw.githubusercontent.com/bigjosh/De-Harak-Clock-Controller/master/bbb/ledscape-config.json`
6. `sync`

Note that we remove `wicd` since it uses lots of CPU when idle and this increases the chances of the ARM having memory contention when the PRUs go to access the GPIO pins, which causes white flashes. 

## If make a new SD flasher with the current system state

1. Put in 4Gb SD card
2. `sudo /opt/scripts/tools/eMMC/beaglebone-black-make-microSD-flasher-from-eMMC.sh`
3. `nano /boot/uEnv.txt`
4. Uncomment the flasher line `cmdline=init=/opt/scripts/tools/eMMC/init-eMMC-flasher-v3.sh`
