#include <zephyr/kernel.h>
#include <sequence.h>

int main(void)
{
	printk('Hello from runner!');
	run();
	return 0;
}
