# Pico development - Getting started

## Requirements
Windows system with WSL2 and VS Code installed.

## Linux system dependencies

```
# sudo apt install --no-install-recommends git cmake ninja-build gperf \
  ccache dfu-util device-tree-compiler wget \
  python3-dev python3-pip python3-setuptools python3-tk python3-wheel xz-utils file \
  make gcc gcc-multilib g++-multilib libsdl2-dev libmagic1
```
## Zephyr SDK installation
Install west - Zephyr multitool
```
# pip3 install --user -U west
# echo 'export PATH=~/.local/bin:"$PATH"' >> ~/.bashrc
# source ~/.bashrc
```
Download SDK
```
# mkdir -p ~/workspace/libs
# wget https://github.com/zephyrproject-rtos/sdk-ng/releases/download/v0.16.1/zephyr-sdk-0.16.1_linux-x86_64.tar.xz
# tar -xvf zephyr-sdk-0.16.1_linux-x86_64.tar.xz
# cd zephyr-sdk-0.16.1
# ./setup.sh
```
## VS code workspace schema
``` 
# mkdir -p ~/workspace/zephyrproject
# west init ~/workspace/zephyrproject
# cd ~/workspace/zephyrproject
# west update
# west zephyr-export
# git clone https://github.com/Nukersson/zephyr_vscode_workspace.git
```

## Pico and Picoprobe USB device passthrough to WSL
###  On Windows
Bind usb ports:

Install [USBIPd](https://github.com/dorssel/usbipd-win/), windows software for sharing locally connected USB devices to other machines, including Hyper-V guests and WSL2. 

```
# usbipd bind --force --hardware-id 2e8a:000a
# usbipd bind --force --hardware-id 2e8a:000c
```

> [!NOTE]  
> * Raspberry Pi Pico is reported by system as device with hardware ID `2e8a:000a`.
> *  Raspberry Pi Debug Probe probe is reported by system as device with hardware ID `2e8a:000c`.

### On Ubuntu
Install required packages
```
# sudo apt install linux-tools-generic hwdata
# sudo update-alternatives --install /usr/local/bin/usbip usbip /usr/lib/linux-tools/*-generic/usbip 20
```

Test it, on ubuntu `lsusb` should show:

```
(...)
Bus 001 Device 002: ID 2e8a:000c Raspberry Pi Debug Probe (CMSIS-DAP)
(...)
```

###  On Windows
Attach ports to WSL:

```
# usbipd wsl attach --hardware-id 2e8a:000a
# usbipd wsl attach --hardware-id 2e8a:000c
```


> [!IMPORTANT]
>	Attaching is required every time you restart WSL /  your computer, I suggest to create a simple Powershell script `AttachDebugger.ps1` with code:
>
>	```
> 	usbipd wsl attach --hardware-id 2e8a:000a
>	usbipd wsl attach --hardware-id 2e8a:000c
>
>	Write-Host "Press any key to continue..."
>	$Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
>	```
>
> 	to quickly attach devices. "Press any key..." is added > due to prevent console window close.

> [!WARNING]  
>	If running scripts is disabled on your Windows open PowerShell as an Administrator (the command will fail otherwise) and run the following command:
>
>	```
>	Set-ExecutionPolicy RemoteSigned
>	```

# Install OpenOCD

```
# sudo apt install automake autoconf build-essential texinfo libtool libftdi-dev libusb-1.0-0-dev
# cd ~/workspace/libs
# git clone https://github.com/raspberrypi/openocd.git --branch rp2040-v0.12.0 --depth=1
# cd openocd
# ./bootstrap
# ./configure
# make -j4
# sudo make install
```
Configure udev
```
# wget https://raw.githubusercontent.com/raspberrypi/openocd/rp2040/contrib/60-openocd.rules
# sudo mv 60-openocd.rules /etc/udev/rules.d/
# sudo service udev restart
# sudo udevadm control --reload-rules && sudo udevadm trigger
```


Test it (debug probe must be connected to your pico debug pins), run in console:
```
# openocd -f interface/cmsis-dap.cfg -f target/rp2040.cfg
```
It is important to run without `sudo`.

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

# Download Scramjet repository

```
# cd ~/workspace
# git clone git@github.com:scramjetorg/platform-pico-development.git
```

# VS Code configuration files:

## Zephyr.code-workspace

Change file under path: `~/workspace/zephyrproject/zephyr_vscode_workspace/Zephyr.code-workspace`

To following:

```
{
	"folders": [
		{
			"path": "."
		},
		{
			"name": "zephyrproject",
			"path": "../"
		},
		{
			"name": "AppUnderDev",
			"path": "../../platform-pico-development"
		},
		{
			"name": "ZephyrTests",
			"path": "../zephyr/tests/net/socket/websocket"
		},
		{
			"name": "BootloaderUnderDev",
			"path": "../bootloader/mcuboot/boot/zephyr"
		}
	],

	"settings": {
		"west": "west",
		"twister":  {
			"host_test_arch": "qemu_x86",
		},
		// Board support package settings:
		"bsp": {
			"cpu": "",  // must be used if multi core system (put _m4 or _m7 here for example)
			"soc": "RP2040",
			"board": "rpi_pico",
			"board_root": "${workspaceFolder:zephyrproject}/zephyr",
			"board_path": "${config:bsp.board_root}/boards/arm/${config:bsp.board}",
			"svd": "${workspaceFolder}/modules/hal/rpi_pico/src/rp2040/hardware_regs/rp2040.svd",
		},

		// App settings:
		"app": {
			"name": "${workspaceFolder:AppUnderDev}",
			"build_dir": "${workspaceFolder:AppUnderDev}/build",
			"zephyr_config": "",  // -DOVERLAY_CONFIG=<path_relative_to_sample> use ; for multiple files
			"zephyr_dtc_overlay": "",  // "-DDTC_OVERLAY_FILE=boards/nucleo_f303re.overlay"  // -DDTC_OVERLAY_FILE=<path_relative_to_sample> use ; for multiple files
			"compile_args": ""
		},

		// Bootloader app settings:
		"app_boot": {
			"name": "${workspaceFolder:BootloaderUnderDev}",
			"build_dir": "${workspaceFolder:BootloaderUnderDev}/build",
			"zephyr_config": "",  // -DOVERLAY_CONFIG=<path_relative_to_sample> use ; for multiple files
			"zephyr_dtc_overlay": "",  // "-DDTC_OVERLAY_FILE=boards/nucleo_f303re.overlay"  // -DDTC_OVERLAY_FILE=<path_relative_to_sample> use ; for multiple files
			"compile_args": ""
		},

		"C_Cpp.default.compilerPath": "${env:GNUARMEMB_TOOLCHAIN_PATH}/bin/arm-zephyr-eabi-gcc",
		"C_Cpp.default.compileCommands": "${config:app.build_dir}/compile_commands.json",
		"C_Cpp.default.includePath": [
			"${workspaceFolder:zephyrproject}/zephyr",
			"${env:GNUARMEMB_TOOLCHAIN_PATH}/arm-zephyr-eabi/include",
			"${env:GNUARMEMB_TOOLCHAIN_PATH}/arm-zephyr-eabi/sys-include"
		],
		
		"cmake.configureOnOpen": false,

		"files.associations": {
		},

		// The number of spaces a tab is equal to. This setting is overridden
		// based on the file contents when `editor.detectIndentation` is true.
		"editor.tabSize": 8,

		// Insert spaces when pressing Tab. This setting is overriden
		// based on the file contents when `editor.detectIndentation` is true.
		"editor.insertSpaces": false,

		// When opening a file, `editor.tabSize` and `editor.insertSpaces`
		// will be detected based on the file contents. Set to false to keep
		// the values you've explicitly set, above.
		"editor.detectIndentation": false,
		"editor.rulers": [80],

		"editor.cursorBlinking": "smooth",

		"files.trimFinalNewlines": true,
		"editor.formatOnSave": false,
		"editor.codeActionsOnSave": [],

		"editor.renderWhitespace": "all",

		"files.watcherExclude": {
			"**/.git/objects/**": true,
			"**/.git/subtree-cache/**": true,
			"**/node_modules/**": true,
			"**/tmp/**": true,
			"**/.git": true,
			"**/.svn": true,
			"**/.hg": true,
			"**/CVS": true,
			"**/.DS_Store": true,
			"**/node_modules": true,
			"**/bower_components": true,
			"**/dist/**": true,
			"**/log/**": true,
			"**/logs/**": true,
			"**/.fdk/**": true,
			"**/.west/**": true,
			"**/.vscode/**": true,
			"${workspaceRoot}/../zephyr/**": true
		},
		"files.exclude": {
			"**/.git/objects/**": true,
			"**/.git/subtree-cache/**": true,
			"**/node_modules/**": true,
			"**/tmp/**": true,
			"**/.git": true,
			"**/.svn": true,
			"**/.hg": true,
			"**/CVS": true,
			"**/.DS_Store": true,
			"**/node_modules": true,
			"**/bower_components": true,
			"**/dist/**": true,
			"**/log/**": true,
			"**/.fdk/**": true,
			"**/.west/**": true
		},
		"search.exclude": {
			"**/.git/objects/**": true,
			"**/.git/subtree-cache/**": true,
			"**/node_modules/**": true,
			"**/tmp/**": true,
			"**/.git": true,
			"**/.svn": true,
			"**/.hg": true,
			"**/CVS": true,
			"**/.DS_Store": true,
			"**/node_modules": true,
			"**/bower_components": true,
			"**/dist/**": true,
			"**/log/**": true,
			"**/.west/**": true
		},
		"editor.renderControlCharacters": false,
		"cortex-debug.variableUseNaturalFormat": false
	}
}
```

# launch.json

Change file under path: ~/workspace/zephyrproject/zephyr_vscode_workspace/.vscode/launch.json

To following:

```
{
	"version": "2.0.0",
	// See available parameters under:
	// 	https://github.com/Marus/cortex-debug/blob/master/src/common.ts#LL249C25-L249C25
	"configurations": [
	{
		"name": "Flash & Debug AppUnderDev",
		"cwd": "${workspaceFolder:AppUnderDev}",
		"executable": "${config:app.build_dir}/zephyr/zephyr.elf",
		"request": "launch",
		"type": "cortex-debug",
		"servertype": "openocd",
		"interface": "swd",
		"device": "${config:bsp.soc}",
		"targetId": "${config:bsp.board}",
		"boardId": "1",
		"toolchainPrefix": "${userHome}/workspace/libs/zephyr-sdk-0.16.1/arm-zephyr-eabi/bin/arm-zephyr-eabi",
		"armToolchainPath": "${env:GNUARMEMB_TOOLCHAIN_PATH}",
		"svdFile": "${config:bsp.svd}",
		"showDevDebugOutput": "raw",
		"configFiles": [
			"/interface/cmsis-dap.cfg",
			"/target/rp2040.cfg"
		    ],
	},
	{
		"name": "Flash & Debug BootloaderUnderDev",
		"cwd": "${workspaceFolder:BootloaderUnderDev}",
		"executable": "${config:app_boot.build_dir}/zephyr/zephyr.elf",
		"request": "launch",
		"type": "cortex-debug",
		"servertype": "openocd",
		"interface": "swd",
		"device": "${config:bsp.soc}",
		"targetId": "${config:bsp.board}",
		"boardId": "1",
		"toolchainPrefix": "arm-zephyr-eabi",
		"armToolchainPath": "${env:GNUARMEMB_TOOLCHAIN_PATH}",
		"svdFile": "${config:bsp.svd}",
		"showDevDebugOutput": "raw",
		"configFiles": [
				"${config:bsp.debug_config}"
			]
	}
	]
}
```
# Run workspace in VS Code

In VS Code select: `File`->`Open Workspace from File` and select path: `~/workspace/zephyrproject/zephyr_vscode_workspace/Zephyr.code-workspace`

Press `Ctrl + Shift + P` and select `Tasks: Run build tasks`

Run `West Build app`

You should get something like that:

```
(...)
-- west build: building application
[1/12] Performing build step for 'second_stage_bootloader'
ninja: no work to do.
[8/8] Linking C executable zephyr/zephyr.elf
Memory region         Used Size  Region Size  %age Used
      BOOT_FLASH:         256 B        256 B    100.00%
           FLASH:       18797 B    2096896 B      0.90%
             RAM:        9640 B       264 KB      3.57%
        IDT_LIST:          0 GB         2 KB      0.00%
Converting to uf2, output size: 38400, start address: 0x10000000
Wrote 38400 bytes to zephyr.uf2
 *  Terminal will be reused by tasks, press any key to close it. 
 ```

After hitting `F5` (or select `Start Debugging`) you should be able to flash and debug your Pico.

Sources:

* https://github.com/robotdad/piconotes
* https://learn.microsoft.com/en-us/windows/wsl/connect-usb
* https://github.com/KozhinovAlexander/zephyr_vscode_workspace
* https://github.com/Marus/cortex-debug#usage
* https://gist.github.com/smittytone/81bac3ab9a78e21bd46ed20b0ba17d72