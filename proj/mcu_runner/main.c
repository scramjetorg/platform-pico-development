#include <zephyr/kernel.h>
#include <zephyr/sys/printk.h>
#include <zephyr/usb/usb_device.h>
#include <zephyr/drivers/uart.h>
#include <sequence.h>
#include <stdio.h>

#define PROTOCOL_HEADER_SIZE 3
// #define SCRAMJET_IN 256
// #define SCRAMJET_OUT 256

// RING_BUF_DECLARE(scramjet_in, SCRAMJET_IN)
// RING_BUF_DECLARE(scramjet_out, SCRAMJET_OUT)

static const struct device *const dev_scramjet = DEVICE_DT_GET(DT_ALIAS(scramjet_uart));
static const struct device *const dev_console = DEVICE_DT_GET(DT_CHOSEN(zephyr_console));

#define UART_ASCI_FORMAT
enum sc_command {
#ifdef UART_ASCI_FORMAT
	Ping = '0',
#else
	Ping = 0,
#endif
	Pong,
	Control,
	In,
	Out,
	Error,
	Undefined
};
typedef uint8_t sc_cmd_t;

enum sc_control_command {
#ifdef UART_ASCI_FORMAT
	NameRequest = 816,
#else
	NameRequest = 0,
#endif
	NameResponse,
};
typedef uint16_t sc_control_cmd_t;

typedef union {
	uint8_t	prot_header[PROTOCOL_HEADER_SIZE];
	struct {
		sc_cmd_t cmd_code;
		uint16_t id; 
	} Ping;
	struct  {
		sc_cmd_t cmd_code;
		uint16_t id; 
	} Pong;
	struct {
		sc_cmd_t cmd_code;
		sc_control_cmd_t control_cmd_code; 
	} Control;
	struct {
		sc_cmd_t cmd_code;
		uint16_t size;
	} In;
	struct {
		sc_cmd_t cmd_code;
		uint16_t size;
	} Out;
	struct {
		sc_cmd_t cmd_code;
		uint16_t size;
	} Error;
} sc_protocol_t;

typedef struct uart_data_rx
{
    uint8_t uart_buf[PROTOCOL_HEADER_SIZE];
    uint8_t uart_buf_len;
} uart_data_rx_t;

uart_data_rx_t scramjet_uart = {{Undefined}, 0 };

void print_uart(const unsigned char* msg, size_t size)
{
	for (size_t i = 0; i < size; i++) {
		uart_poll_out(dev_scramjet, msg[i]);
	}
	return;
}

void print_error(const unsigned char* msg)
{
	uint16_t err_len = strlen(msg);
	char errorHeader[PROTOCOL_HEADER_SIZE];
	errorHeader[0] = Error;
	sprintf(errorHeader + 1, "%x", err_len);
	print_uart(errorHeader, PROTOCOL_HEADER_SIZE);
	print_uart(msg, err_len);
	return;
}

static void scramjet_io_serial_handler(const struct device *dev, void *user_data)
{
	uart_data_rx_t* data = (uart_data_rx_t*)user_data;
	if (!(uart_irq_update(dev) && uart_irq_rx_ready(dev))){
		return;
	} 
	const sc_protocol_t* proto = (sc_protocol_t*)(data->uart_buf);
	while (true){
		const int bytes_read = uart_fifo_read(dev, data->uart_buf + data->uart_buf_len, PROTOCOL_HEADER_SIZE - data->uart_buf_len);
		if(bytes_read ==  0) break;
		data->uart_buf_len += bytes_read;
		
		if( data->uart_buf_len >= PROTOCOL_HEADER_SIZE){
			printk("prot: %c%c%c\n", proto->prot_header[0], proto->prot_header[1], proto->prot_header[2]); 
			
			switch(proto->prot_header[0]){
				case Ping:
					const sc_protocol_t pong = {{Pong, proto->prot_header[1], proto->prot_header[2]}};
					print_uart(pong.prot_header, PROTOCOL_HEADER_SIZE);
					break;
				case Control:
					printk("ctrl_code1: %d %x", proto->Control.control_cmd_code, proto->Control.control_cmd_code);
					printk("ctrl_code2: %x %x", proto->prot_header[1], proto->prot_header[2]);
					if(proto->Control.control_cmd_code == NameRequest){
						const char* boardName = sequenceName();
#ifdef UART_ASCI_FORMAT
						const sc_protocol_t controlResp = {{Control, '0', '1'}};
#else
						const sc_protocol_t controlResp = {{Control, 0, 1}};
#endif
						print_uart(controlResp.prot_header, PROTOCOL_HEADER_SIZE);

						const uint16_t nameLen = strlen(boardName);

						char nameLenSize[2];
						sprintf(nameLenSize, "%x", nameLen);
						print_uart(nameLenSize, PROTOCOL_HEADER_SIZE);
						print_uart(boardName, nameLen);
					} else {
						const char errCtrlCode[] = "Unknown control_code\r\n";
						print_error(errCtrlCode);
					}
					break;
				default:
					const char errCode[] = "Unknown cmd_code\r\n";
					print_error(errCode);
			}
			data->uart_buf_len = 0;
		}
	}
	return;
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
	
	uart_irq_callback_user_data_set(dev_scramjet, scramjet_io_serial_handler,&scramjet_uart);
	uart_irq_rx_enable(dev_scramjet);

	while (1) {
		// printd("Hello, runner!\r\n",16);
		// run();
		// k_sleep(K_MSEC(1000));
		k_sleep(K_MSEC(100));
	}
	return 0;
}
