cmake_minimum_required(VERSION 3.15)
project(Greeter LANGUAGES C)

include(GNUInstallDirs)

if(NOT TARGET LibGreet::LibGreet)
   find_package(LibGreet 2.0 CONFIG REQUIRED)
endif()

add_executable(greeter greeter.c)
target_link_libraries(greeter PUBLIC LibGreet::LibGreet)
install(TARGETS greeter DESTINATION "${CMAKE_INSTALL_BINDIR}")
