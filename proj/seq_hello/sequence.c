#include <zephyr/kernel.h>
#include <sequence.h>

const char* sequenceName(void){
	return "Sequence hello";
}

int run(void)
{
	printk("Hello from userspace!\n");
	return 0;
}
