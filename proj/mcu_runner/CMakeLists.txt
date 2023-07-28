cmake_minimum_required(VERSION 3.20)

project(ScramjetMCURunner)

target_link_libraries(app PUBLIC ScramjetSequenceHelloLib)

target_sources(app PRIVATE main.c)
