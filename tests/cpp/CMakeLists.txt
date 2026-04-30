include(FetchContent)
FetchContent_Declare(
    googletest
    GIT_REPOSITORY https://github.com/google/googletest.git
    GIT_TAG v1.15.2
)
set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
FetchContent_MakeAvailable(googletest)

add_executable(photonics_tests
    test_materials.cpp
    test_tmm.cpp
    test_bragg.cpp
)
target_link_libraries(photonics_tests PRIVATE photonics_core_lib GTest::gtest_main)

include(GoogleTest)
gtest_discover_tests(photonics_tests)
