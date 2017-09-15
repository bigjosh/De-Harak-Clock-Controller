# De Harrak Clock Controller Software

This software runs on a Raspberry Pi and controlls 72 independent digit pannels attached to the same network as the Pi. 

Each digit pannel is running the LEDscape package to drive the attached LEDs.

The master controller uses DNSMASQ to hand out IP addresses and maps those address to digits by MAC address using DNS entries in the dhcp-hosts file.

Each panel gets a DNS name that is mapped to its location on the clock. The top row of digits are `T01` - `T12`, and the bottom 5 rows are `B00` - `B59`.

# Operation

The clock runs continusly using the local linux time. The timezone is set inside the `clockmode.sh` script, as are the colors for hours, minutes, seconds, and background. 

In the case when minutes andsSeconds are on the smae digit, seconds win. 

The background is currently set to turn on at 8PM and off at 7AM. This save a bit of power and wear as the dim background light is not visible durring daylight.

# Installation

Easiest way to install is to use the release in this repo to flash a new SD card. Then `cd` into the repo and do a `git pull` to make sure everything is up to date.

Use `tzselect` to set the right timezone if nessisary.

## Manual install

Copy the included dnsmasq.conf to /etc.

Make sure no other DCHP server is running (I'm looking at you dhcpdcd).

Make sure DNSMASQ is enabled to run at startup.

Use `sudo raspi-config` to disable graphical desktop on boot (boot into CLI).

# Starting up the clock

You should only need to do this after a power outage.

`cd` into the repo and run...

`./nh.sd clockmode.sh`

This runs the standard clock mode. The `nh` script runs it with `nohup` so it will keep running even after the temrinal session ends. 

Then go look at the clock. You should see most digits looking like a clock, but a few with rainbow patterns. This digits did not successfully connect to the network on boot (see [here](https://groups.google.com/forum/#!topic/beagleboard/9mctrG26Mc8%5B176-200%5D) for info). To fix these digits, they must be repowered. Find a column on the clock that has one or more unconnect digits and then find the circuit breaker that controls that column. Switch the breaker off and count to 3-missashippi and then switch back on. Give the column a minute to boot and usually all of the digits in that panel will successfuly connect. repeat until all digits are showing the clock pattern. 

# Replacing a digit panel

All panels are identical, so can easily be swapped out with spares in case of problems. 

Once a digit has been swapped, you need to update the DHCP/DNS entry for the MAC address of the new panel to map to the correct location on the clock. To do this, on the Pi command line run...

`digitpicker.sh`

Scroll though and find the old panel that was located in the replaced position and change the name to something like `deadH20`. Next look for en entery with a name like `beaglebone` or `*` rather than a good name. This is likely the new panel. Hit enter and it should blink on the clock. Next enter the correct DNS name for this position (i.e. `H20`) and press enter. Then save the file and restart the clockmode program so the changes take effect. 

# Backdoor

There is a hidden wifi access point in the digit 57 box to give direct access to the internal network from in front of the clock. This can be helpful in cases where you are trying to find a digit and the wifi in the lobby is not working.  SSID and key are written on paper inside the binder in the clock equipment room. 

# Extending the display

There are several scripts showing examples of how to update the display for modes other than clock. All use OPC over UDP to set the pixels in each digit. `ticktest.sh` is a good place to start. It lights up each digit in sequence with red, green, blue, and white. Note that you can use any RGB color. To run `ticktest`, enter...

`./nh.sh ticktest.sh`

For more complicated displays, C is likely faster than shell scripts. The beginings of some C drivers are in this reop. 

# Getting a diagnostic view of the digit statuses

You can use the `checkdigits.sh` script to get a quick overview of which digits are working...

```
pi@raspberrypi:~/De-Harak-Clock-Controller $ ./checkdigits.sh
H means host not found in DNS
P means fialed to ping

  h01  Hh02H  h03   h04  Hh05H  h06  Hh07H Hh08H  h09   h10  Hh11H  h12
  m00  Hm01H  m02   m03  Hm04H  m05  Hm06H Hm07H  m08   m09  Hm10H  m11
  m12  Hm13H  m14   m15  Hm16H  m17  Hm18H Hm19H  m20   m21  Hm22H  m23
  m24  Hm25H  m26   m27  Hm28H  m29  Hm30H Hm31H  m32   m33  Hm34H  m35
  m36  Hm37H  m38   m39  Hm40H  m41  Hm42H Hm43H  m44   m45  Hm46H  m47
  m48  Hm49H  m50   m51  Hm52H  m53  Hm54H Hm55H  m56   m57  Hm58H  m59
pi@raspberrypi:~/De-Harak-Clock-Controller $

```

In this view, for example, digits `h01` and m17` are woring fine but `h11` and `12` do not have DNS entries (yikes!!!).

# The `nextsecond` utility

This simple sleeps until the next second on the clock. If it is 10:55:22.75 and you run `./nextsecond`, then it will sleep for about 0.25 seconds. 

The clock uses this to always start an update at the top of a second.

You can test that it works by running...

`./nextsecond; date "+%N"`

It will print the number of nanoseconds since the last round second> I should always be < 010000000, which is 10,000,000ns, which is 10ms. 

