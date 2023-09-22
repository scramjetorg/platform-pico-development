#include <sequence.h>

const char* sequenceName(void){
	return "Pico#000";
}

int run(readCb read, writeCb write)
{
	uint8_t readBuffer[16];
	uint16_t dataRead = read(readBuffer, 16);
	if(dataRead > 0)
		write(readBuffer, dataRead);
	return 0;
}
