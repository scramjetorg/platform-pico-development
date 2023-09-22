#include <sequence.h>

const char* sequenceName(void){
	return "Pico#000";
}

int run(readCb read, writeCb write)
{
	uint8_t readBuffor[16];
	uint16_t dataRead = read(readBuffor, 16);
	if(dataRead > 0)
		write(readBuffor, dataRead);
	return 0;
}
