
#include <zephyr/drivers/adc.h>
#include <zephyr/drivers/gpio.h>
#include "sequence.h"

const char* sequenceName(void){
	return "PicoLed#000";
}

#define SEND_BUF_SIZE 2
#define LED0_NODE DT_ALIAS(led0)

static const struct gpio_dt_spec led = GPIO_DT_SPEC_GET(LED0_NODE, gpios);

int run(readCb read, writeCb write)
{
	uint8_t readBuffer[4] = {0, 0, 0, 0};
	uint16_t dataRead = 0;
	int err;

	if (!gpio_is_ready_dt(&led)) {
		return 0;
	}
	err = gpio_pin_configure_dt(&led, GPIO_OUTPUT_ACTIVE);
	if (err < 0) {
		printk("Unable to configure led pin\n");
		return 0;
	}

	gpio_pin_set_dt(&led, 0);

	while (1) {
		k_sleep(K_MSEC(500));
		dataRead = read(readBuffer, 16);
		
		if(dataRead > 0){
			switch (readBuffer[0]){
				case 2:
					gpio_pin_set_dt(&led, 0);
					break;
				case 3:
					gpio_pin_set_dt(&led, 1);
					break;
				default:
					break;
			}
		}
	}

	return 0;
}
