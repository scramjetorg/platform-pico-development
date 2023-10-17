cmake_minimum_required(VERSION 3.20)

set(BOARD "rpi_pico")

find_package(Zephyr)

project(PicoDevelopment)

zephyr_library_include_directories(include)

add_subdirectory(proj/seq_hello)
# add_subdirectory(proj/seq_led)
# add_subdirectory(proj/seq_mic)

add_subdirectory(proj/mcu_runner)