cmake_minimum_required(VERSION 3.20)
project(adjacent_web LANGUAGES CXX)

if(NOT EMSCRIPTEN)
    message(FATAL_ERROR "Configure this project through emcmake")
endif()

set(BUILD_TESTING OFF CACHE BOOL "" FORCE)
add_subdirectory(../lib adjacent-core)

add_executable(adjacent_web src/bindings.cpp)
target_link_libraries(adjacent_web PRIVATE adjacent::adjacent)
target_compile_features(adjacent_web PRIVATE cxx_std_17)
target_link_options(adjacent_web PRIVATE
    -O0
    --bind
    -sMODULARIZE=1
    -sEXPORT_ES6=1
    -sALLOW_MEMORY_GROWTH=1
    -sENVIRONMENT=web,worker,node
    -sASSERTIONS=1
)
set_target_properties(adjacent_web PROPERTIES
    OUTPUT_NAME adjacent
    SUFFIX ".js"
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/dist"
)
