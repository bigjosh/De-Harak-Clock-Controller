leds: leds.c
	g++ leds.c -o leds
	chmod +x leds

udpopc: udpopc.c
	g++ udpopc.c -o udpopc
	chmod +x udpopc
    
nextsecond: nextsecond.c
	g++ nextsecond.c -o nextsecond
	chmod +x nextsecond
