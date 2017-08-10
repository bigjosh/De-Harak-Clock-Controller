// Wait until the next second rolls over
// Use sleep rather than polling


#include <unistd.h>
#include <sys/time.h>



int main(void) {

	unsigned int microseconds;
	
	struct timeval  tv;
	gettimeofday(&tv, NULL);

	
	// Calculate time until next round second...
	
	microseconds = 1000000 - (tv.tv_usec);
	
	usleep(microseconds);
	
	return(0);
}