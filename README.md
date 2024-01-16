# Scramjet-pico-development
This repo is PoC how to use [zephyr](https://www.zephyrproject.org/) library to build 
a runtime enviroment that can be run on microcontrolers (Raspberry Pico used in example) with ability to separate control layer of microcontroler unit from user layer used to analyze data.

Comunication is based on UART protocol and allow passing commands to contor layer and data to user layer.


Controll layer allows to recognize instances of our runner on serial devices, identify user sequences installed on MCU, and report errors.

User layer gives possibility to stream data from and to user sequence using serial connection.


## Scramjet MCU development

1. [Pico development](docs/pico-develpment.md)
2. [STM32 programming](docs/stm32-programmer.md)
3. [Scramjet communication protocol](docs/srcamjet-protocol.md)
