#pragma once 
#include <zephyr/kernel.h>

const char* sequenceName();

typedef uint16_t (*writeCb)(const uint8_t* data, uint16_t size);
typedef uint16_t (*readCb)(uint8_t* data, uint16_t size);

int run(readCb read, writeCb write);