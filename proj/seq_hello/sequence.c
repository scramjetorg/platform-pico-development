#include <zephyr/kernel.h>
#include <sequence.h>
int run(void)
{
	printk("Hello from userspace!\n");
	return 0;
}
