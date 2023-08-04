cmake_minimum_required(VERSION 3.20)

find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})

project(ScramjetMCURunner)

FILE(GLOB app_sources *.c)

target_sources(app PRIVATE ${app_sources})

target_link_libraries(app PUBLIC ScramjetSequenceHelloLib)