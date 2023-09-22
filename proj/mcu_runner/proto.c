#include <stdint.h>
#include <string.h>
#include "proto.h"

void driver_initialize(scramjet_driver_t* driver, writeToRunnerCb send, const char* boardName){
	driver->state = WaitingForCommand;
	driver->headerLength = 0;
	uint8_t* input = k_malloc(SCRAMJET_INPUT_SIZE);
	ring_buf_init(&driver->inputRingBuff, SCRAMJET_INPUT_SIZE, input);
	driver->flood = false;
	driver->writeRunnerCb = send;
	driver->boardName = boardName;
	driver->nameLen = strlen(driver->boardName);
}

void driver_remove(scramjet_driver_t* driver){
	k_free(driver->inputRingBuff.buffer);
}

uint32_t driver_put_claim(scramjet_driver_t* driver, uint8_t **data){
	if(driver->state == InputReceiving){
		uint16_t inputToRead = (uint16_t)driver->header[1] << 8 | driver->header[2];
		return ring_buf_put_claim(&driver->inputRingBuff, data, inputToRead);
	} else {
		if(driver->headerLength > 2){
			data = NULL;
			return 0;
		}
		*data = driver->header + driver->headerLength;
		return MAX_HEADER_SIZE - driver->headerLength;
	}
}
int driver_put_finish(scramjet_driver_t* driver, uint32_t size){
	if(driver->state == InputReceiving){
		ring_buf_put_finish(&driver->inputRingBuff, size);
		
		uint16_t inputToRead = (uint16_t)driver->header[1] << 8 | driver->header[2];
		inputToRead -= size;
		driver->header[1] = (uint16_t)inputToRead >> 8;
		driver->header[2] = (uint8_t)inputToRead;
		if(inputToRead == 0) {
			driver->headerLength = 0;
			driver->state = WaitingForCommand;
		}
		return size;
	} else {
		if(MAX_HEADER_SIZE - driver->headerLength - size >= 0){
			driver->headerLength += size;
			return 0;
		}
		return -EINVAL;
	}
}

void driver_send_cmd(scramjet_driver_t* driver, cmd_t command, uint16_t payload_size, const uint8_t* payload){
	driver->header[0] = (cmd_t)command;
	driver->header[1] = (uint16_t)payload_size >> 8;
	driver->header[2] = (uint8_t)payload_size;
	driver->writeRunnerCb(driver->header, MAX_HEADER_SIZE);
	if(payload_size > 0)
		driver->writeRunnerCb(payload, payload_size);
};

void driver_parse_buffer(scramjet_driver_t* driver){
	if(driver->state == InputReceiving)	return;
	
	switch(driver->header[0]){
		case Ping:
			if(driver->headerLength < 3) return;
			driver->header[0] = (cmd_t)Pong;
			driver->writeRunnerCb(driver->header, 3);
			driver->headerLength = 0;
			break;
		case NameRequest:
			driver_send_cmd(driver, (cmd_t)NameResponse, driver->nameLen, driver->boardName);
			driver->headerLength = 0;
			break;
		case FloodOn:
			driver->flood = true;
			driver->headerLength = 0;
			return;
		case FloodOff:
			driver->flood = false;
			driver->headerLength = 0;
			return;
		case Input:
			if(driver->headerLength < 3) return;
			driver->state =	InputReceiving;
			break;
		default:
			const char errCode[] = "Unknown cmd_code";
			driver_send_cmd(driver, (cmd_t)Error, 16, errCode);
			driver->headerLength = 0;
			return;
	}
}
