#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <math.h>
#include <time.h>
#include <sys/timerfd.h>
#include <ctype.h>

#include <unistd.h>
#include <string.h>
#include <sys/types.h>

#include <sys/socket.h>
#include <netinet/in.h>
#include <netdb.h> 
#include <arpa/inet.h>

#include "udpopc.h"

#define OPC_HEADERSIZE 4 		// 4 bytes in opc header
#define OPC_BUFFERSIZE (OPC_HEADERSIZE + OPC_BYTECOUNT)


OPC_BUFFER *createOPCbuffer(unsigned buffer_len) {

	OPC_BUFFER *opc_buffer = malloc(OPC_HEADERSIZE + buffer_len);

	if (!opc_buffer) return opc_buffer;

	opcbuffer[0]=0x00;		// Channel=0 
	opcbuffer[1]=0x00;		// Command=0	
	opcbuffer[2]=(OPC_BYTECOUNT>>8);		// len MSB
	opcbuffer[3]=(OPC_BYTECOUNT&0xff);	// len LSB
	
	return opc_buffer;
}

#define OPCPORT 7890


OPC_SOCKET *createOPCSocket() {

	OPC_SOCKET opc_socket = malloc(sizeof(OPC_SOCKET);

	if (!opc_socket) return opc_socket;
		
	opc_socket->sockfd= socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);

	if (opc_socket->sockfd < 0) {
		free(opc_socket); 
		return(-100);
	}

	int broadcastEnable=1;

	int ret=setsockopt(opc_socket->sockfd, SOL_SOCKET, SO_BROADCAST, &broadcastEnable, sizeof(broadcastEnable));

	if (ret < 0) {
		flclose(opc_socket->sockfd);
		free(opc_socket);
		return(-101);
	}

	reurn(opc_socket);
    
} 


int setOPCdest(OPC_DEST *opc_dest, constr char *dest) {

	struct sockaddr_in serv_addr = opc_dest->serv_addr;

	inet_pton(AF_INET, dest , serv_addr );
	
	bzero(serv_addr, sizeof(serv_addr));
	serv_addr->sin_family = AF_INET;
	serv_addr->sin_port = htons(OPCPORT);
	
	return( inet_pton(AF_INET, dest , serv_addr.sin_addr)));
	
	//	return(inet_aton(deststr, serv_addr.sin_addr)));		// This version does direct IP no DNS

	//(struct sockaddr*)&serv_addr

}

int sendOPC(OPC_SOCKET *opc_socket, OPC_DEST *opc_dest, OPC_BUFFER *opc_buffer) {

	return(  sendto( opc_socket->sockfd, opc_buffer->buffer , opc_buffer->size, 0, OPC_DEST->serv_addr , sizeof(struct serv_addr) ) );  // 0 is the flags

}


void sendOPC( OPC_SOCKET opc_socket , ) {
	
	initopcheader();			// TODO: Only do this once per run

    // printf("start... pins=%d, rowsperpin=%d\r\n", PIN_COUNT , ROWS_PER_PIN);
	
    unsigned char *m = opcbuffer+OPC_HEADERSIZE;	
            
    for( int pin = 0; pin <PIN_COUNT ; pin++ ) {                // OPC packet has each string snet sequentially
        
        for( int row=0; row < ROWS_PER_PIN ; row++ ) {
                       
            int y= ( pin ) + ( row * PIN_COUNT );

           // printf("p,r,y=%d,%d,%d\r\n",pin,row,y);
                                   
            if (y>=SIZE_Y) {      // Of the screen?
                                
                for( int i=0;i<SIZE_X * 3;i++) {
                    
                    *(m++) = 0x00;                                        
                    // Send zeros as padding
                    
                }
                
            } else {                
                        
                if (row&1) {  // Alternating rows go back and forth
                                        
                    int x=SIZE_X;
            
                    while (x--) {
                                        
                        *(m++) = (r[x][y]) ;
                        *(m++) = (g[x][y]) ;                        
                        *(m++) = (b[x][y]) ;
                        
                    }
                    
                } else {
                    
                    for( int x=0; x<SIZE_X;x++) {

                        *(m++) = (r[x][y]) ;
                        *(m++) = (g[x][y]) ;
                        *(m++) = (b[x][y]) ;
                     
                    }                
               }                
            }
            
			
        }
    }
    
    int x=sendto(sockfd, opcbuffer, OPC_BUFFERSIZE , 0, (struct sockaddr*)&serv_addr, slen);  // 0 is the flags
    
	    
}

#define SETRGB( x, y , red , green, blue ) {r[x][y]=red;g[x][y]=green;b[x][y]=blue;}
    
unsigned char parsehexdigit( const char s) {
    
    if (isdigit(s)) return( s - '0' );
    if (islower(s) && s<='f') return( s - 'a' + 10);
    if (isupper(s) && s<='F') return( s - 'A' + 10);
    return(0);
}


unsigned char parsehexdigits( const char *s ) {
    
    return( ( parsehexdigit(*s) *16  ) + parsehexdigit( *(s+1)) );
    
}

#define MIN(a,b) (((a)<(b))?(a):(b))

int main( int argc, char **argv) {
	
	printf("LEDs (c)2016 josh levine [josh.com]\r\n");
    
    if (argc!=7) {
            fprintf(stderr,"Usage  : leds dest_ip  rgb left right top bot \r\n");
            fprintf(stderr,"         RGB color format XXXXXX (FFFFFF=white)\r\n");
            
            fprintf(stderr,"Example: leds 192.168.174.2 0000FF 0 %d  0 %d  = Full panel to blue\r\n", SIZE_X , SIZE_Y );
            
            return(1);        
    }
	
	printf("dest ip : %s\r\n", argv[1]);
	
    opensocket( argv[1] );
    
	if (sockfd < 0) {
		fprintf( stderr , "ERROR opening socket");    
		return(1);
	}	
    
	printf("Socket established.\r\n");
	
	const char *colorString = argv[2];
	
    unsigned char r1 = parsehexdigits(colorString);
    unsigned char g1 = parsehexdigits(colorString+2);
    unsigned char b1 = parsehexdigits(colorString+4);	
    
    printf( "Color={%X,%X,%X}\r\n" , r1, g1, b1);
    
	unsigned char left 		= atoi( argv[3] );	
	unsigned char right 	= atoi( argv[4] );	
	unsigned char top 		= atoi( argv[5] );	
	unsigned char bottom 	= atoi( argv[6] );	
        
    printf("l=%d r=%d t=%d b=%d\r\n",left,right,top,bottom);
		
   for( int x=left; x< MIN(SIZE_X , right)  ; x++) {
        
        for(int y=top;y<= MIN(SIZE_Y, bottom) ;y++) {
            
            r[x][y] = r1;
            g[x][y] = g1;
            b[x][y] = b1;
            
            
        }
    }
    
    sendOPCPixels();

	printf("Sent.\r\n");
        
    return(0);
    
}
