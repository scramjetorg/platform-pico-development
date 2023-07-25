
## Picoprobe USB device passthrough to WSL
###  On Windows

Install USBIPd, windows software for sharing locally connected USB devices to other machines, including Hyper-V guests and WSL 2.
https://github.com/dorssel/usbipd-win/


Pico probe is reported by system as device with hardware ID `2e8a:000a` and `2e8a:000c`.
```
# usbipd bind --force --hardware-id 2e8a:000a
# usbipd wsl attach --hardware-id 2e8a:000a
```

```
# usbipd bind --force --hardware-id 2e8a:000c
# usbipd wsl attach --hardware-id 2e8a:000c
```

### On Ubuntu
```
# sudo apt install linux-tools-generic hwdata
# sudo update-alternatives --install /usr/local/bin/usbip usbip /usr/lib/linux-tools/*-generic/usbip 20
```

Test it, on ubuntu `lsusb` should show:

```
Bus 001 Device 002: ID 2e8a:000c Raspberry Pi Debug Probe (CMSIS-DAP)
```

# OpenOCD

```
# sudo apt install automake autoconf build-essential texinfo libtool libftdi-dev libusb-1.0-0-dev
# git clone https://github.com/raspberrypi/openocd.git --branch rp2040-v0.12.0 --depth=1
# cd openocd
# ./bootstrap
# ./configure
# make -j4
# sudo make install
```

```
# wget https://raw.githubusercontent.com/raspberrypi/openocd/rp2040/contrib/60-openocd.rules
# sudo mv 60-openocd.rules /etc/udev/rules.d/
# sudo service udev restart
# sudo udevadm control --reload-rules && sudo udevadm trigger
```


Test it!

Run:
```
# openocd -f interface/cmsis-dap.cfg -f target/rp2040.cfg
```
It is important to run wihout `sudo`.

You should get something like that:

```
Open On-Chip Debugger 0.12.0-g97d1e6e (2023-07-25-13:35)
(...)
Info : Using CMSIS-DAPv2 interface with VID:PID=0x2e8a:0x000c, serial=XXXXXXX
Info : CMSIS-DAP: SWD supported
Info : CMSIS-DAP: Atomic commands supported
Info : CMSIS-DAP: Test domain timer supported
Info : CMSIS-DAP: FW Version = 2.0.0
Info : CMSIS-DAP: Interface Initialised (SWD)
Info : SWCLK/TCK = 0 SWDIO/TMS = 0 TDI = 0 TDO = 0 nTRST = 0 nRESET = 0
Info : CMSIS-DAP: Interface ready
Info : clock speed 100 kHz
Info : SWD DPIDR 0x0bc12477, DLPIDR 0x00000001
Info : SWD DPIDR 0x0bc12477, DLPIDR 0x10000001
Info : [rp2040.core0] Cortex-M0+ r0p1 processor detected
(...)
Info : Listening on port 3333 for gdb connections
```