#include <zephyr/kernel.h>
#include <zephyr/sys/printk.h>
#include <zephyr/usb/usb_device.h>
#include <zephyr/drivers/uart.h>
#include "proto.h"
#include "sequence.h"
#include <stdio.h>
#include <zephyr/sys/ring_buffer.h>

RING_BUF_DECLARE(sc_ring_in, 256);

static const struct device *const dev_scramjet = DEVICE_DT_GET(DT_ALIAS(scramjet_uart));
static const struct device *const dev_console = DEVICE_DT_GET(DT_CHOSEN(zephyr_console));

uint16_t print_uart(const uint8_t* msg, uint16_t size)
{
	for (uint16_t i = 0; i < size; i++) {
		uart_poll_out(dev_scramjet, msg[i]);
	}
	return size;
}

void print_error(const unsigned char* msg)
{
	uint16_t err_len = strlen(msg);
	unsigned char errorHeader[MAX_HEADER_SIZE];
	fillHeader(errorHeader, Error, err_len);
	print_uart(errorHeader, MAX_HEADER_SIZE);
	print_uart(msg, err_len);
	return;
}

static void scramjet_io_serial_handler(const struct device *dev, void *user_data)
{
	Scramjet_driver_t* driver = (Scramjet_driver_t*)user_data;
	if (!(uart_irq_update(dev) && uart_irq_rx_ready(dev))){
		return;
	}
	while(true){
		uint8_t *data;
		uint16_t size = driver_put_claim(driver, &data, SCRAMJET_INPUT_SIZE);
		const int bytes_read = uart_fifo_read(dev, data, size);
		driver_put_finish(driver, bytes_read);
		if(bytes_read ==  0) break;
		parse(driver);
	}
	
	return;
}

uint32_t read(uint8_t* data, uint32_t size){
	return 0;
}
uint16_t write(uint8_t* data, uint16_t size){
	unsigned char outHeader[MAX_HEADER_SIZE];
	fillHeader(outHeader, Output, size);
	print_uart(outHeader, size);
	print_uart(data, size);
	return size;
}

int main(void)
{
	if (usb_enable(NULL))
	{
		return 0;
	}
	printk("INIT: USB enabled");

	uint32_t dtr_console = 0;
	while (!dtr_console) {
		uart_line_ctrl_get(dev_console, UART_LINE_CTRL_DTR, &dtr_console);
		k_sleep(K_MSEC(100));
		printk("INIT: Wait for console...\n");
	}

	printk("INIT: Console enabled\n");
	
	uint32_t dtr_management = 0;
	while (!dtr_management) {
		uart_line_ctrl_get(dev_scramjet, UART_LINE_CTRL_DTR, &dtr_management);
		k_sleep(K_MSEC(100));
		printk("INIT: Wait for management...\n");

	}

	printk("INIT: Management enabled\n");
	
	uart_line_ctrl_set(dev_scramjet, UART_LINE_CTRL_DCD, 1);
	uart_line_ctrl_set(dev_scramjet, UART_LINE_CTRL_DSR, 1);
	
	Scramjet_driver_t driver;
	initialize_driver(&driver, print_uart, sequenceName());

	uart_irq_callback_user_data_set(dev_scramjet, scramjet_io_serial_handler,&driver);
	uart_irq_rx_enable(dev_scramjet);


	while (1) {
		if(driver.flood){
			printk("71830\n");
		}
		// run();
		// k_sleep(K_MSEC(1000));
		k_sleep(K_MSEC(100));
	}
	remove_driver(&driver);
	return 0;
}
