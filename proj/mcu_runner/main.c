#include <zephyr/kernel.h>
#include <zephyr/sys/printk.h>
#include <zephyr/usb/usb_device.h>
#include <zephyr/drivers/uart.h>
#include <sequence.h>

const struct device *const dev_console = DEVICE_DT_GET(DT_CHOSEN(zephyr_console));
const struct device *const dev_scramjet = DEVICE_DT_GET(DT_ALIAS(scramjet_uart));

typedef struct uart_data_rx
{
    char* rx_data;
    uint8_t rx_len;
    uint8_t rx_cnt;

} uart_data_rx_t;


uart_data_rx_t scramjet_uart = {NULL, 16, 0};

void printd(const char* msg, int size)
{
	for (int i = 0; i < size; i++)
	{
		uart_poll_out(dev_scramjet, msg[i]);
	}
}

static void scramjet_io_interrupt_handler(const struct device *dev, void *user_data)
{
	uart_data_rx_t* data = (uart_data_rx_t*)user_data;
 	uint8_t c;

	while (uart_irq_update(dev) && uart_irq_is_pending(dev)) 
	{
		if (!uart_irq_update(dev))
		{
			return;
		}

		if (!uart_irq_rx_ready(dev))
		{
			return;
		}

		uart_fifo_read(dev, &c, 1);
		data->rx_data[data->rx_cnt] = c;
		data->rx_cnt++;
		
		if(data->rx_cnt == data->rx_len+1 || c == '\r')
		{
			uart_irq_rx_disable(dev);
			
			printk("[SCRAMJET CONSOLE] %s\r\n", data->rx_data);
			memset(data->rx_data, 0, data->rx_len);		
			data->rx_cnt = 0;
			uart_irq_rx_enable(dev);
		}
	}
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
	
	scramjet_uart.rx_data = k_malloc(scramjet_uart.rx_len+1);
	
	if (scramjet_uart.rx_data == NULL)
	{
		printk("INIT: No RX memory\n");
	}

	memset(scramjet_uart.rx_data, '\0', scramjet_uart.rx_len);
	
	uart_irq_callback_user_data_set(dev_scramjet, scramjet_io_interrupt_handler,&scramjet_uart);
	uart_irq_rx_enable(dev_scramjet);

	while (1) {
		printd("Hello, runner!\r\n",16);
		run();
		k_sleep(K_MSEC(1000));
	}
	
}
