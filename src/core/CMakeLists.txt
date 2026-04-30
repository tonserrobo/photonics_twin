add_library(photonics_core STATIC
    src/materials.cpp
    src/tmm.cpp
    src/bragg.cpp
)

target_include_directories(photonics_core PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_compile_features(photonics_core PUBLIC cxx_std_17)
