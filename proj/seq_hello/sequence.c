#include <sequence.h>

const char* sequenceName(void){
	return "Sequence hello";
}

int run(readCb read, writeCb write)
{
	uint8_t readBuffor[16];
	uint16_t dataRead = read(readBuffor, 16);
	write(readBuffor, dataRead);
	return 0;
}
