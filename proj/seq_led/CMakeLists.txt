cmake_minimum_required(VERSION 3.20)

project(ScramjetSequenceHelloLib)

include_directories("../../include")

add_library(ScramjetSequenceHelloLib STATIC sequence.c)

target_link_libraries(ScramjetSequenceHelloLib PUBLIC zephyr_interface)
