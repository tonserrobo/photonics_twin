cmake_minimum_required(VERSION 3.24)
project(photonics_twin LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

option(PHOTONICS_BUILD_TESTS "Build C++ unit tests" ON)

add_subdirectory(src/core)

if(SKBUILD)
    add_subdirectory(src/bindings)
endif()

if(PHOTONICS_BUILD_TESTS AND NOT SKBUILD)
    enable_testing()
    add_subdirectory(tests/cpp)
endif()
