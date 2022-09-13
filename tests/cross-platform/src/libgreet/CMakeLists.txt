cmake_minimum_required(VERSION 3.15)
project(LibGreet
   VERSION 2.1.42
   LANGUAGES C)

include(GNUInstallDirs)
include(GenerateExportHeader)

# do not export any symbols by default
set(CMAKE_CXX_VISIBILITY_PRESET hidden)
set(CMAKE_VISIBILITY_INLINES_HIDDEN 1)

# Find dependency if target does not exist yet in build tree
if (NOT TARGET LibHoller::LibHoller)
   find_package(LibHoller 1.0 CONFIG REQUIRED)
endif()

# Add library
add_library(LibGreet greet.c greet.h)
add_library(LibGreet::LibGreet ALIAS LibGreet)
target_include_directories(LibGreet
   PRIVATE ${CMAKE_CURRENT_BINARY_DIR}
   PUBLIC $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}>
   $<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}>)
target_link_libraries(LibGreet PUBLIC LibHoller::LibHoller)

set_target_properties(LibGreet PROPERTIES
	VERSION "${LibGreet_VERSION}"
	SOVERSION "2"
	POSITION_INDEPENDENT_CODE "${BUILD_SHARED_LIBS}"
)

# Generate header for export/import definitions
generate_export_header(LibGreet)

# install rules
install(TARGETS LibGreet EXPORT LibGreetTargets)
install(FILES greet.h ${PROJECT_BINARY_DIR}/libgreet_export.h TYPE INCLUDE)

# package stuff
include(CMakePackageConfigHelpers)
write_basic_package_version_file(
  "${CMAKE_CURRENT_BINARY_DIR}/LibGreetConfigVersion.cmake"
  VERSION ${LibGreet_VERSION}
  COMPATIBILITY SameMajorVersion
)

export(EXPORT LibGreetTargets
  FILE "${CMAKE_CURRENT_BINARY_DIR}/LibGreetTargets.cmake"
  NAMESPACE LibGreet::
)
configure_file(LibGreetConfig.cmake.in
  "${CMAKE_CURRENT_BINARY_DIR}/LibGreetConfig.cmake"
  COPYONLY
)

set(ConfigPackageLocation lib/cmake/LibGreet)
install(EXPORT LibGreetTargets
  FILE
    LibGreetTargets.cmake
  NAMESPACE
    LibGreet::
  DESTINATION
    ${ConfigPackageLocation}
)
install(
  FILES
    "${CMAKE_CURRENT_BINARY_DIR}/LibGreetConfig.cmake"
    "${CMAKE_CURRENT_BINARY_DIR}/LibGreetConfigVersion.cmake"
  DESTINATION
    ${ConfigPackageLocation}
)
