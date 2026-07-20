cmake_minimum_required(VERSION 3.16)
project(ScheduleParser)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
# Указываем, куда складывать готовый экзешник 
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_SOURCE_DIR}/exec)

find_package(PkgConfig REQUIRED)
pkg_check_modules(RE2 REQUIRED re2)

set(OPENXLSX_BUILD_SAMPLES OFF CACHE BOOL "" FORCE)
set(OPENXLSX_BUILD_TESTS OFF CACHE BOOL "" FORCE)
set(OPENXLSX_BUILD_DOCS OFF CACHE BOOL "" FORCE) # Включаем сборку документации
set(REDIS_PLUS_PLUS_BUILD_TEST OFF CACHE BOOL "" FORCE)


# --------------- LIBS -----------------------
add_subdirectory(libs/hiredis)

# 1. Жестко говорим, где лежат заголовочные файлы hiredis (на уровень выше, в папке libs)
set(HIREDIS_HEADER "${CMAKE_SOURCE_DIR}/libs" CACHE PATH "" FORCE)

# 2. Жестко говорим, что в качестве библиотеки нужно использовать CMake-таргет "hiredis",
# который только что создался командой add_subdirectory выше.
set(HIREDIS_LIB hiredis CACHE STRING "" FORCE)

# Отключаем тесты
set(REDIS_PLUS_PLUS_BUILD_TEST OFF CACHE BOOL "" FORCE)
add_subdirectory(libs/redis-plus-plus)
add_subdirectory(libs/OpenXLSX)
# --------------- LIBS -----------------------


add_executable(worker 
    # Исходники 
    src/worker.cpp
    src/Utils.cpp
    src/ParserObjects.cpp
    src/redis_wrapper.cpp
    # Заголовки 
    include/Utils.hpp
    include/ParserObjects.hpp
    include/redis_wrapper.hpp
    include/config.hpp
)

target_include_directories(worker PRIVATE ${CMAKE_SOURCE_DIR}/include)
target_link_libraries(worker OpenXLSX ${RE2_LIBRARIES} redis++)

add_custom_target(run
    COMMAND ./worker
    DEPENDS worker
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}/exec
)
