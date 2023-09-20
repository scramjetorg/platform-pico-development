
# STM32 Programmer

## On WSL
Download `en.stm32cubeprg-lin-v2-14-0.zip`
```
# cd ~/
# wget https://www.st.com/content/ccc/resource/technical/software/utility/group0/06/ed/fd/c3/aa/6c/41/14/stm32cubeprg-lin-v2-14-0/files/stm32cubeprg-lin-v2-14-0.zip/jcr:content/translations/en.stm32cubeprg-lin-v2-14-0.zip
```

Install CubeProgrammer in default path
```
# unzip ~/en.stm32cubeprg-lin-v2-14-0.zip
# chmod +x  SetupSTM32CubeProgrammer-2.14.0.linux
# ./SetupSTM32CubeProgrammer-2.14.0.linux
```
> [!NOTE]  
> Keep in mind that is GUI installer so you need a X server on Windows if you work in WSL.
>

## Getting started with Nucleo F303K8

### On Windows
Attach Programmer via USBIPd to WSL:
```
# usbipd bind --force --hardware-id 0483:374b
# usbipd wsl attach  --hardware-id 0483:374b --auto-attach
```

> [!NOTE]  
> Nucleo F303K8 Debug Probe is reported by system as device with hardware ID `0483:374b`.
>


### Test building
Default overlay in Zephyr for `Nucleo F303K8` uses wrong pin (P15) which do not exists. We have to change it to other.
So, create `<ZEPHYR_DIR>/samples/drivers/uart/echo_bot/app.overlay` with content:

```
/ {
	chosen {
		zephyr,console = &usart2;
	};
};

&usart2 {
	pinctrl-0 = <&usart2_tx_pb3 &usart2_rx_pb4>;
	pinctrl-names = "default";
	current-speed = <115200>;
	status = "okay";
};
```

Compile it
```
# west build -d ~/build -b nucleo_f303k8  <ZEPHYR_DIR>/samples/drivers/uart/echo_bot/
```

Flash
```
# west flash
```

Connect to UART via pins D13/D12

Remove `<ZEPHYR_DIR>/samples/drivers/uart/echo_bot/app.overlay`