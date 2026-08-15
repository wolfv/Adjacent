cmake_minimum_required(VERSION 3.16)
project(adjacent VERSION 0.2.0 LANGUAGES CXX)

include(GNUInstallDirs)
include(CMakePackageConfigHelpers)

option(BUILD_TESTING "Build the C++ test suite" OFF)

find_package(xtensor REQUIRED)

add_library(adjacent
    src/expression.cpp
    src/expression_vector.cpp
    src/gaussian_method.cpp
    src/equation_system.cpp
    src/expr_basis.cpp
)
add_library(adjacent::adjacent ALIAS adjacent)
set_target_properties(adjacent PROPERTIES
    CXX_STANDARD 17
    CXX_STANDARD_REQUIRED ON
    CXX_EXTENSIONS OFF
    POSITION_INDEPENDENT_CODE ON
    VERSION ${PROJECT_VERSION}
    SOVERSION ${PROJECT_VERSION_MAJOR}
    EXPORT_NAME adjacent
)
target_link_libraries(adjacent PUBLIC xtensor)
target_include_directories(adjacent PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}>
)

install(TARGETS adjacent
    EXPORT adjacentTargets
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
    INCLUDES DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}
)
install(DIRECTORY include/ DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/adjacent)
install(EXPORT adjacentTargets
    FILE adjacentTargets.cmake
    NAMESPACE adjacent::
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/adjacent
)
configure_package_config_file(
    ${CMAKE_CURRENT_SOURCE_DIR}/cmake/adjacentConfig.cmake.in
    ${CMAKE_CURRENT_BINARY_DIR}/adjacentConfig.cmake
    INSTALL_DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/adjacent
)
write_basic_package_version_file(
    ${CMAKE_CURRENT_BINARY_DIR}/adjacentConfigVersion.cmake
    VERSION ${PROJECT_VERSION}
    COMPATIBILITY SameMajorVersion
)
install(FILES
    ${CMAKE_CURRENT_BINARY_DIR}/adjacentConfig.cmake
    ${CMAKE_CURRENT_BINARY_DIR}/adjacentConfigVersion.cmake
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/adjacent
)

if(BUILD_TESTING)
    enable_testing()
    add_executable(adjacent_test tests/test.cpp)
    target_link_libraries(adjacent_test PRIVATE adjacent::adjacent)
    add_test(NAME adjacent_test COMMAND adjacent_test)
endif()
