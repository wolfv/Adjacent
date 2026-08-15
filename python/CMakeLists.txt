cmake_minimum_required(VERSION 3.16)
project(adjacent_python VERSION 0.2.0 LANGUAGES CXX)

find_package(Python COMPONENTS Interpreter Development.Module REQUIRED)
find_package(pybind11 CONFIG REQUIRED)
find_package(adjacent CONFIG REQUIRED)

pybind11_add_module(_adjacent src/py_interface.cpp)
target_compile_features(_adjacent PRIVATE cxx_std_17)
target_link_libraries(_adjacent PRIVATE adjacent::adjacent)

install(TARGETS _adjacent
    LIBRARY DESTINATION adjacent
    RUNTIME DESTINATION adjacent
)
