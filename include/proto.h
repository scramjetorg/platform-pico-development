#include <zephyr/sys/ring_buffer.h>

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

typedef uint16_t (*sequenceInputCb)(uint8_t* data_out, uint16_t size);
typedef uint16_t (*sequenceOutputCb)(const uint8_t* data, uint16_t size);

typedef struct sequence_context {
	sequenceInputCb in;
	sequenceOutputCb out;
} sequence_context_t;

typedef uint16_t (*readFromRunnerCb)(uint8_t* data, uint16_t size);

typedef struct scramjet_controller {
	readFromRunnerCb readRunnerCb;
	sequence_context_t context;
} scramjet_controller_t;

typedef uint16_t (*writeToRunnerCb)(const uint8_t* data, uint16_t size);

typedef struct Scramjet_driver {
	state_t state;
	struct ring_buf headerRingBuff;
	struct ring_buf inputRingBuff;
	uint8_t outputHeader[MAX_HEADER_SIZE];
	bool flood;
	writeToRunnerCb writeRunnerCb;
    const char* boardName;
    uint16_t nameLen;
} Scramjet_driver_t;

void initialize_driver(Scramjet_driver_t* driver, writeToRunnerCb send, const char* boardName){
	driver->state = waitingForCommand;
	uint8_t* header = k_malloc(MAX_HEADER_SIZE);
	ring_buf_init(&driver->headerRingBuff, MAX_HEADER_SIZE, header);
	uint8_t* input = k_malloc(SCRAMJET_INPUT_SIZE);
	ring_buf_init(&driver->inputRingBuff, SCRAMJET_INPUT_SIZE, input);
	driver->flood = false;
    driver->writeRunnerCb = send;
    driver->boardName = boardName;
    driver->nameLen = strlen(driver->boardName);
}

void remove_driver(Scramjet_driver_t* driver){
	k_free(driver->headerRingBuff.buffer);
	k_free(driver->inputRingBuff.buffer);
}

void handlePing(Scramjet_driver_t* driver){
	if(ring_buf_size_get(&driver->headerRingBuff) < 3) return;
    uint8_t *ring_data;
    uint8_t claimedSize = ring_buf_get_claim(&driver->headerRingBuff, &ring_data, 3);
    driver->outputHeader[0] = (cmd_t)Pong;
    driver->outputHeader[1] = ring_data[1];
    driver->outputHeader[2] = ring_data[2];
    ring_buf_get_finish(&driver->headerRingBuff, claimedSize);

    driver->writeRunnerCb(driver->outputHeader, 3);
}

uint32_t driver_put_claim(Scramjet_driver_t* driver, uint8_t **data, uint32_t size){
    if(driver->state == InputReceiving){
        return ring_buf_put_claim(&driver->inputRingBuff, data, size);
    } else {
        return ring_buf_put_claim(&driver->headerRingBuff, data, size);
    }
}
int driver_put_finish(Scramjet_driver_t* driver, uint32_t size){
    if(driver->state == InputReceiving){
        return ring_buf_put_finish(&driver->inputRingBuff, size);
    } else {
        return ring_buf_put_finish(&driver->headerRingBuff, size);
    }
}

void parse(Scramjet_driver_t* driver){
	// ring_buf_size_get(&driver->headerRingBuff);
    if(driver->state == InputReceiving){

	} else {
		uint8_t ringByte;
		uint32_t size = ring_buf_peek(&driver->headerRingBuff, &ringByte, 1);
		if(size == 0) return;
		switch(ringByte){
			case Ping:
				handlePing(driver);
				break;
			case NameRequest:
                driver->outputHeader[0] = (cmd_t)NameResponse;
                driver->outputHeader[1] = (uint16_t)driver->nameLen >> 8;
                driver->outputHeader[2] = (uint8_t)driver->nameLen;
                driver->writeRunnerCb(driver->outputHeader, 3);
                driver->writeRunnerCb(driver->boardName, driver->nameLen);
                ring_buf_get(&driver->headerRingBuff, NULL, 1);
				break;
			case FloodOn:
				driver->flood = true;
                ring_buf_get(&driver->headerRingBuff, NULL, 1);
				return;
			case FloodOff:
				driver->flood = false;
                ring_buf_get(&driver->headerRingBuff, NULL, 1);
				return;
			case Input:
                if(ring_buf_size_get(&driver->headerRingBuff) < 3) return;
				driver->state =	InputReceiving;
				break;
			default:
                const char errCode[] = "Unknown cmd_code\r\n";
                driver->outputHeader[0] = (cmd_t)Error;
                driver->outputHeader[1] = 0;
                driver->outputHeader[2] = 20;
                driver->writeRunnerCb(driver->outputHeader, 3);
                driver->writeRunnerCb(errCode, 20);
				ring_buf_get(&driver->headerRingBuff, NULL, 1);
				return;
		}
	}

}

void fillHeader(unsigned char* header, cmd_t command, uint16_t size){
	header[0] = command;
	header[1] = (uint16_t)size >> 8;
	header[2] = (uint8_t)size;
}
