find_package(pybind11 CONFIG REQUIRED)

pybind11_add_module(photonics_core MODULE
    photonics_core.cpp
)
target_link_libraries(photonics_core PRIVATE photonics_core_lib)
set_target_properties(photonics_core PROPERTIES OUTPUT_NAME "photonics_core")

# Install rule for scikit-build-core to pick up the .so/.pyd.
if(SKBUILD)
    install(TARGETS photonics_core DESTINATION photonics_core)
endif()
