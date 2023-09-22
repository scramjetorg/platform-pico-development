#ifndef SCARMJET_DRIVER
#define SCARMJET_DRIVER

#include <zephyr/sys/ring_buffer.h>

#ifndef EINVAL
#define EINVAL 22
#endif

#define MAX_HEADER_SIZE 3
#define SCRAMJET_INPUT_SIZE 256

/* Enumeration representing the driver work state*/
typedef enum {
	WaitingForCommand,
	InputReceiving,
} state_t;

/* Enumeration representing the scramjet protocol commands*/
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

/**
 * @brief A structure to represent a scramjet driver
 */
typedef struct scramjet_driver {
	state_t state;
	uint8_t header[MAX_HEADER_SIZE];
	uint8_t headerLength;
	struct ring_buf inputRingBuff;
	bool flood;
	writeToRunnerCb writeRunnerCb;
	const char* boardName;
	uint16_t nameLen;
} scramjet_driver_t;

/**
 * @brief Initialize a scramjet driver.
 *
 * This routine initializes a scramjet driver, prior to its first use.
 *
 * @param  driver  Address of scramjet driver.
 * @param send Callback used to send data to a communication channel.
 * @param boardName Pointer to a string name of the user sequence.
 */
void driver_initialize(scramjet_driver_t* driver, writeToRunnerCb send, const char* boardName);

/**
 * @brief Free allocated resources by the scramjet driver.
 *
 * @param[in]  driver  Address of scramjet driver.
 */
void driver_remove(scramjet_driver_t* driver);

/**
 * @brief Get address of a valid data in driver buffers depending on state.
 *
 * With this routine, memory copying can be reduced since internal buffer
 * can be used directly by the user. Once data is processed it must be freed
 * using @ref driver_put_finish.
 *
 * @param[in]  driver  Address of scramjet driver.
 * @param[out] data Pointer to the address. It is set to a location within
 *		    internal buffers.
 *
 * @return Number of valid bytes in the provided buffer.
 */
uint32_t driver_put_claim(scramjet_driver_t* driver, uint8_t **data);

/**
 * @brief Indicate number of bytes written to allocated buffers.
 *
 * The number of bytes must be equal to or lower than the sum corresponding
 * to all preceding @ref driver_put_claim invocations (or even 0).
 *
 * @param  driver  Address of scramjet driver.
 * @param  size Number of valid bytes in the allocated buffers.
 *
 * @retval 0 Successful operation.
 * @retval -EINVAL Provided if size exceeds free space in the buffer.
 */
int driver_put_finish(scramjet_driver_t* driver, uint32_t size);

/**
 * @brief Send command with provided data.
 *
 * If payloadSize is equal to 0 only protocol header is send.
 *
 * @param  driver  Address of scramjet driver.
 * @param  command  Code of command to send.
 * @param  payloadSize Size of payload (in bytes) to send.
 * @param  payload Pointer to the begining of data to be send as payload.
 *
 * @retval 0 Successful operation.
 * @retval -EINVAL Provided if size exceeds free space in the buffer.
 */
void driver_send_cmd(scramjet_driver_t* driver, cmd_t command, uint16_t payloadSize, const uint8_t* payload);

/**
 * @brief Start parsing driver state based on current data in buffers.
 *
 * @param  driver  Address of scramjet driver.
 */
void driver_parse_buffer(scramjet_driver_t* driver);

#endif /* SCARMJET_DRIVER */