
#include <zephyr/drivers/adc.h>
#include <zephyr/drivers/gpio.h>
#include "sequence.h"

const char* sequenceName(void){
	return "PicoMic#000";
}

#if !DT_NODE_EXISTS(DT_PATH(zephyr_user)) || \
	!DT_NODE_HAS_PROP(DT_PATH(zephyr_user), io_channels)
#error "No suitable devicetree overlay specified"
#endif

#define SEND_BUF_SIZE 2

static const struct adc_dt_spec adc_chan0 =
    ADC_DT_SPEC_GET_BY_IDX(DT_PATH(zephyr_user), 0);

int run(readCb read, writeCb write)
{
	uint8_t readBuffer[4] = {0, 0, 0, 0};
	uint16_t dataRead = 0;
	int err;
	bool readAdc = false;
	uint16_t buf;
	uint8_t sendBuf[SEND_BUF_SIZE];

	struct adc_sequence_options opt = {
		.interval_us = 125,
	};

	struct adc_sequence sequence = {
		.options = &opt,
		.buffer = &buf,
		.buffer_size = sizeof(buf),
	};

	if (!adc_is_ready_dt(&adc_chan0)) {
		printk("ADC controller device %s not ready\n", adc_chan0.dev->name);
		return 0;
	}
	err = adc_channel_setup_dt(&adc_chan0);
	if (err < 0) {
		printk("Could not setup channel (%d)\n", err);
		return 0;
	}

	(void)adc_sequence_init_dt(&adc_chan0, &sequence);

	while (1) {
		k_sleep(K_MSEC(0));
		dataRead = read(readBuffer, 16);
		
		if(dataRead > 0){
			switch (readBuffer[0]){
				case 0:
					readAdc = false;
					break;
				case 1:
					readAdc = true;
					break;
				default:
					break;
			}
		}

		if(readAdc == false) 
			continue;

		err = adc_read(adc_chan0.dev, &sequence);
		if (err < 0) {
			sendBuf[0] = 0;
			sendBuf[1] = 0;
			write(sendBuf, SEND_BUF_SIZE);
			continue;
		}
		sendBuf[0] = buf >> 8;
		sendBuf[1] = (uint8_t)buf;
		write(sendBuf, SEND_BUF_SIZE);
	}

	return 0;
}
