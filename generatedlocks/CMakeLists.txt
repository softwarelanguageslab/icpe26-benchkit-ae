# generatedlocks/CMakeLists.txt
#
# Build configuration for auto-generated tilt lock wrappers.
#
# The C source files in src/ are generated at experiment setup time by
# lib/lockgen/tiltgen.py (for libvsync locks: CAS, TTAS, Ticket, MCS,
# Hemlock) and lib/lockgen/hmcs.py (for the NUMA-aware HMCS lock).
# The generated header for HMCS is placed in include/.
#
# This CMakeLists.txt compiles each generated .c file into an individual
# shared library (.so), which tilt combines and loads via
# LD_PRELOAD to interpose pthread_mutex calls with the selected lock.
#
# Dependencies:
#   - deps/libvsync/    (atomic primitives and spinlock implementations)
#   - deps/tilt/        (tilt interposition header)
#
# ARM-specific: On aarch64, LSE atomics are enabled (-march=armv8-a+lse).

cmake_minimum_required(VERSION 3.22)

project(tiltgenlock C)

# Add dependencies
add_subdirectory(${CMAKE_SOURCE_DIR}/../deps/libvsync/ build_libvsync)
include_directories(include ${CMAKE_SOURCE_DIR}/../deps/tilt/include/)

# Path to generated lock files
set(LOCKS_DIR ${CMAKE_SOURCE_DIR}/src)

# Glob all .c files in the generated directory
file(GLOB LOCK_FILES "${LOCKS_DIR}/*.c")

# Loop through each lock file to create a library
foreach(LOCK_FILE ${LOCK_FILES})
    # Extract the lock name from the file (e.g., tilt_mcslock from tilt_mcslock.c)
    get_filename_component(LOCK_NAME ${LOCK_FILE} NAME_WE)

    # Add a shared library for each lock
    add_library(${LOCK_NAME} SHARED ${LOCK_FILE})

    # Link the vsync library to each lock
    target_link_libraries(${LOCK_NAME} vsync)

    # Add strong warning flags for GCC and Clang
    if(CMAKE_C_COMPILER_ID MATCHES "GNU|Clang")
        target_compile_options(${LOCK_NAME} PRIVATE
            -Wall
            -Wextra
            -Wpedantic
            -Wshadow
            -Wconversion
            -Wsign-conversion
            -Wnull-dereference
            -Wdouble-promotion
            -Wformat=2
            #-Werror
        )
    endif()

    # Add specific options for ARM architectures
    if(CMAKE_SYSTEM_PROCESSOR MATCHES "aarch64" OR CMAKE_SYSTEM_PROCESSOR MATCHES "armv8")
        target_compile_options(${LOCK_NAME} PRIVATE -march=armv8-a+lse)
    endif()
endforeach()
