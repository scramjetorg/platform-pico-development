#include <zephyr/kernel.h>
#include <zephyr/usb/usb_device.h>
#include <zephyr/drivers/uart.h>
#include <stdio.h>
#include "proto.h"
#include "sequence.h"

static const struct device *const dev_scramjet = DEVICE_DT_GET(DT_CHOSEN(zephyr_console));

uint16_t print_uart(const uint8_t* msg, uint16_t size)
{
	for (uint16_t i = 0; i < size; i++) {
		uart_poll_out(dev_scramjet, msg[i]);
	}
	return size;
}

static void scramjet_io_serial_handler(const struct device *dev, void *user_data)
{
	Scramjet_driver_t* driver = (Scramjet_driver_t*)user_data;
	if (!(uart_irq_update(dev) && uart_irq_rx_ready(dev))){
		return;
	}
	while(true){
		uint8_t *data;
		uint16_t size = driver_put_claim(driver, &data);
		const int bytes_read = uart_fifo_read(dev, data, size);
		driver_put_finish(driver, bytes_read);
		if(bytes_read == 0) break;
		parse(driver);
	}
	return;
}

Scramjet_driver_t driver;

uint16_t read(uint8_t* data, uint16_t size){
	uint8_t claimedSize = ring_buf_get_claim(&driver.inputRingBuff, &data, size);
	ring_buf_get_finish(&driver.inputRingBuff, claimedSize);
	return 0;
}

uint16_t write(const uint8_t* data, uint16_t size){
	output(&driver, data, size);
	return size;
}

int main(void)
{
#ifdef CONFIG_USB_DEVICE_STACK
	if (usb_enable(NULL))
		return 0;
#endif
	
	uint32_t dtr_management = 0;
	while (!dtr_management) {
		uart_line_ctrl_get(dev_scramjet, UART_LINE_CTRL_DTR, &dtr_management);
		k_sleep(K_MSEC(100));
	}

	uart_line_ctrl_set(dev_scramjet, UART_LINE_CTRL_DCD, 1);
	uart_line_ctrl_set(dev_scramjet, UART_LINE_CTRL_DSR, 1);
	
	// Scramjet_driver_t driver;
	initialize_driver(&driver, print_uart, sequenceName());

	int ret = uart_irq_callback_user_data_set(dev_scramjet, scramjet_io_serial_handler,&driver);
	if (ret < 0) {
		if (ret == -ENOTSUP) {
			printk("Interrupt-driven UART API support not enabled\n");
		} else if (ret == -ENOSYS) {
			printk("UART device does not support interrupt-driven API\n");
		} else {
			printk("Error setting UART callback: %d\n", ret);
		}
	}

	uart_irq_rx_enable(dev_scramjet);

	while (1) {
		if(driver.flood){
			print_uart("71830\n", 7);
		}
		// if(ring_buf_size_get(&driver.inputRingBuff) >= 5){
		// 	uint8_t *ring_data;
		// 	uint8_t claimedSize = ring_buf_get_claim(&driver.inputRingBuff, &ring_data, 5);
		// 	output(&driver, ring_data, claimedSize);
		// 	ring_buf_get_finish(&driver.inputRingBuff, claimedSize);
		// 	k_sleep(K_MSEC(100));
		// }
		run(read, write);
		k_sleep(K_MSEC(100));
	}
	remove_driver(&driver);
	return 0;
}
