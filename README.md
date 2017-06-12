# De Harrak Clock Controller Software

This software runs on a Raspberry Pi and controlls 72 independant digit pannels attached to the same network. 

Each digit pannel is running the LEDscape package to drive the attached LEDs.

The panels get this IP address from the controller on boot using DHCP.

The master controller uses DNSMASQ to hand out IP addresses and maps those address to digits by MAC address using DNS entries in the dhcp-hosts file. You can easily map new digits to this file using the `digitpicker.sh` script.

# Installation

Copy the included dnsmasq.conf to /etc.

Make sure no other DCHP server is running (I'm looking at you dhcpdcd).

Make sure DNSMASQ is enabled to run at startup.

Turn on panels.

Use the `digitpicker.sh` script to map panels to DNS names. 


    
 
