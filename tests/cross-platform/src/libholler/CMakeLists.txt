cmake_minimum_required(VERSION 3.15)
project(LibHoller
   VERSION 1.0.0
   LANGUAGES C)

include(GNUInstallDirs)
include(GenerateExportHeader)

# do not export any symbols by default
set(CMAKE_CXX_VISIBILITY_PRESET hidden)
set(CMAKE_VISIBILITY_INLINES_HIDDEN 1)

# Add library
add_library(LibHoller holler.c holler.h)
add_library(LibHoller::LibHoller ALIAS LibHoller)
target_include_directories(LibHoller
   PRIVATE ${CMAKE_CURRENT_BINARY_DIR}
   PUBLIC $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}>
   $<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}>)

set_target_properties(LibHoller PROPERTIES
	VERSION "${LibHoller_VERSION}"
	SOVERSION "1"
	POSITION_INDEPENDENT_CODE "${BUILD_SHARED_LIBS}"
)

# Generate header for export/import definitions
generate_export_header(LibHoller)

# install rules
install(TARGETS LibHoller EXPORT LibHollerTargets)
install(FILES holler.h ${PROJECT_BINARY_DIR}/libholler_export.h TYPE INCLUDE)

# package stuff
include(CMakePackageConfigHelpers)
write_basic_package_version_file(
  "${CMAKE_CURRENT_BINARY_DIR}/LibHollerConfigVersion.cmake"
  VERSION ${LibHoller_VERSION}
  COMPATIBILITY SameMajorVersion
)

export(EXPORT LibHollerTargets
  FILE "${CMAKE_CURRENT_BINARY_DIR}/LibHollerTargets.cmake"
  NAMESPACE LibHoller::
)
configure_file(LibHollerConfig.cmake.in
  "${CMAKE_CURRENT_BINARY_DIR}/LibHollerConfig.cmake"
  COPYONLY
)

set(ConfigPackageLocation lib/cmake/LibHoller)
install(EXPORT LibHollerTargets
  FILE
    LibHollerTargets.cmake
  NAMESPACE
    LibHoller::
  DESTINATION
    ${ConfigPackageLocation}
)
install(
  FILES
    "${CMAKE_CURRENT_BINARY_DIR}/LibHollerConfig.cmake"
    "${CMAKE_CURRENT_BINARY_DIR}/LibHollerConfigVersion.cmake"
  DESTINATION
    ${ConfigPackageLocation}
)
