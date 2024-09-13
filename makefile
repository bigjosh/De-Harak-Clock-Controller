leds: leds.c
	g++ leds.c -o leds
	chmod +x leds

leds: ledsd.c
	g++ ledsd.c -o ledsd
	chmod +x ledsd

udpopc: udpopc.c
	g++ udpopc.c -o udpopc
	chmod +x udpopc
    
nextsecond: nextsecond.c
	g++ nextsecond.c -o nextsecond
	chmod +x nextsecond
