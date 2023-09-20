#include <zephyr/sys/ring_buffer.h>

#ifndef EINVAL
#define EINVAL 22
#endif

#define MAX_HEADER_SIZE 3
#define SCRAMJET_INPUT_SIZE 256

typedef enum {
	waitingForCommand,
	InputReceiving,
} state_t;

enum command {
	Ping = 0,
	Pong,
	NameRequest,
	NameResponse,
	FloodOn,
	FloodOff,
	Input,
	Output,
	Error,
};
typedef uint8_t cmd_t;

typedef uint16_t (*writeToRunnerCb)(const uint8_t* data, uint16_t size);

typedef struct Scramjet_driver {
	state_t state;
	uint8_t protoHeader[MAX_HEADER_SIZE];
	uint8_t protoHeaderLength;
	struct ring_buf inputRingBuff;
	bool flood;
	writeToRunnerCb writeRunnerCb;
	const char* boardName;
	uint16_t nameLen;
} Scramjet_driver_t;

void initialize_driver(Scramjet_driver_t* driver, writeToRunnerCb send, const char* boardName){
	driver->state = waitingForCommand;
	driver->protoHeaderLength = 0;
	uint8_t* input = k_malloc(SCRAMJET_INPUT_SIZE);
	ring_buf_init(&driver->inputRingBuff, SCRAMJET_INPUT_SIZE, input);
	driver->flood = false;
	driver->writeRunnerCb = send;
	driver->boardName = boardName;
	driver->nameLen = strlen(driver->boardName);
}

void remove_driver(Scramjet_driver_t* driver){
	k_free(driver->inputRingBuff.buffer);
}

void handlePing(Scramjet_driver_t* driver){
	if(driver->protoHeaderLength < 3) return;
	driver->protoHeader[0] = (cmd_t)Pong;
	driver->writeRunnerCb(driver->protoHeader, 3);
}

uint32_t driver_put_claim(Scramjet_driver_t* driver, uint8_t **data){
	if(driver->state == InputReceiving){
		uint16_t inputToRead = (uint16_t)driver->protoHeader[1] << 8 | driver->protoHeader[2];
		return ring_buf_put_claim(&driver->inputRingBuff, data, inputToRead);
	} else {
		if(driver->protoHeaderLength > 2){
			data = NULL;
			return 0;
		}
		*data = driver->protoHeader + driver->protoHeaderLength;
		return MAX_HEADER_SIZE - driver->protoHeaderLength;
	}
}
int driver_put_finish(Scramjet_driver_t* driver, uint32_t size){
	if(driver->state == InputReceiving){
		ring_buf_put_finish(&driver->inputRingBuff, size);
		
		uint16_t inputToRead = (uint16_t)driver->protoHeader[1] << 8 | driver->protoHeader[2];
		inputToRead -= size;
		driver->protoHeader[1] = (uint16_t)inputToRead >> 8;
		driver->protoHeader[2] = (uint8_t)inputToRead;
		if(inputToRead == 0) {
			driver->protoHeaderLength = 0;
			driver->state = waitingForCommand;
		}
		return size;
	} else {
		if(MAX_HEADER_SIZE - driver->protoHeaderLength - size >= 0){
			driver->protoHeaderLength += size;
			return 0;
		}
		return -EINVAL;
	}
}

void sendCommandWithPayload(Scramjet_driver_t* driver, cmd_t command, uint16_t payload_size, const uint8_t* payload){
	driver->protoHeader[0] = (cmd_t)command;
	driver->protoHeader[1] = (uint16_t)payload_size >> 8;
	driver->protoHeader[2] = (uint8_t)payload_size;
	driver->writeRunnerCb(driver->protoHeader, MAX_HEADER_SIZE);
	driver->writeRunnerCb(payload, payload_size);
};

void output(Scramjet_driver_t* driver, const uint8_t* payload, uint16_t payload_size){
	return sendCommandWithPayload(driver, (cmd_t)Output, payload_size, payload);
}

void parse(Scramjet_driver_t* driver){
	if(driver->state == InputReceiving)	return;
	
	switch(driver->protoHeader[0]){
		case Ping:
			handlePing(driver);
			driver->protoHeaderLength = 0;
			break;
		case NameRequest:
			sendCommandWithPayload(driver, (cmd_t)NameResponse, driver->nameLen, driver->boardName);
			driver->protoHeaderLength = 0;
			break;
		case FloodOn:
			driver->flood = true;
			driver->protoHeaderLength = 0;
			return;
		case FloodOff:
			driver->flood = false;
			driver->protoHeaderLength = 0;
			return;
		case Input:
			if(driver->protoHeaderLength < 3) return;
			driver->state =	InputReceiving;
			break;
		default:
			const char errCode[] = "Unknown cmd_code";
			sendCommandWithPayload(driver, (cmd_t)Error, 16, errCode);
			driver->protoHeaderLength = 0;
			return;
	}
}
