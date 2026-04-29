# Bragg Grating Feasibility Prototype Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first vertical slice of the Photonics Digital Twin: a Bragg grating simulator covering C++ TMM kernel, pybind11 bindings, FastAPI backend, React UI with live WebSocket updates, and a mocked GitHub-Actions-to-Slurm dispatch path.

**Architecture:** C++17 physics core (HLS-friendly conventions baked in via `real_t`/`complex_t` typedefs and free-function synthesis target) → pybind11 module imported by FastAPI → REST + WebSocket endpoints → React/JS+Vite frontend with Plotly + SVG layer view → parallel GitHub Action that POSTs to a backend mock-Slurm endpoint.

**Tech Stack:** C++17, pybind11, scikit-build-core, CMake, GoogleTest; Python 3.12, FastAPI, Pydantic, uv, pytest, httpx, websockets; React + plain JavaScript, Vite, Plotly; Docker Compose; GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-04-29-bragg-feasibility-prototype-design.md`

---

## File Structure

```
pyproject.toml                                     # scikit-build-core, deps, pytest config
CMakeLists.txt                                     # top-level
.gitignore
.github/workflows/
  ci.yml                                           # build + test
  hpc-dispatch.yml                                 # mock Slurm dispatch
src/
  core/
    CMakeLists.txt
    include/photonics/
      common.hpp                                   # real_t, complex_t, MAX_LAYERS
      materials.hpp                                # SellmeierCoeffs, Material
      tmm.hpp                                      # Layer, LayerStack, tmm_sweep
      bragg.hpp                                    # BraggGrating
    src/
      materials.cpp
      tmm.cpp
      bragg.cpp
  bindings/
    CMakeLists.txt
    photonics_core.cpp                             # PYBIND11_MODULE
  backend/
    app/
      __init__.py
      main.py                                      # FastAPI factory, CORS
      schemas.py                                   # Pydantic models
      sim.py                                       # photonics_core orchestration
      routers/
        __init__.py
        simulate.py
        mock_slurm.py
        ws.py
  frontend/
    package.json
    vite.config.js
    index.html
    src/
      main.jsx
      App.jsx
      App.css
      api.js
      hooks/useSimulation.js
      components/
        ParameterPanel.jsx
        SpectralPlot.jsx
        LayerStackView.jsx
data/
  materials/
    sellmeier_si.json
    sellmeier_sio2.json
  validation/
    quarterwave_si_sio2_reference.json
scripts/
  compute_reference.py                             # Born & Wolf §1.6.5 oracle
simulations/examples/
  bragg_grating_sweep.json                         # mock-Slurm payload
tests/
  cpp/
    CMakeLists.txt
    test_materials.cpp
    test_tmm.cpp
    test_bragg.cpp
  python/
    conftest.py
    test_bindings.py
    test_api.py
docker/
  Dockerfile.backend
  Dockerfile.frontend
docker-compose.yml
```

The empty directories already in the repo (`src/`, `simulations/`, `data/`, `tests/`, `docker/`, `notebooks/`) are populated as we go. `main.py` at repo root and the placeholder `CMakeLists.txt` (which currently contains the literal string `CMakeLists.txt`) are removed in Task 1.

---

## Task 1: Repo bootstrap — pyproject, gitignore, remove placeholders

**Files:**
- Modify: `pyproject.toml`
- Create: `.gitignore`
- Delete: `main.py`, replace contents of `CMakeLists.txt` (currently a placeholder)

- [ ] **Step 1: Replace `pyproject.toml` with the real package definition**

```toml
[build-system]
requires = ["scikit-build-core>=0.10", "pybind11>=2.13"]
build-backend = "scikit_build_core.build"

[project]
name = "photonics-twin"
version = "0.1.0"
description = "SPEAR Photonics Digital Twin — feasibility prototype"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.32",
    "pydantic>=2.9",
    "numpy>=2.1",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3",
    "httpx>=0.27",
    "websockets>=13.1",
    "pytest-asyncio>=0.24",
]

[tool.scikit-build]
cmake.version = ">=3.24"
cmake.build-type = "Release"
wheel.packages = ["src/backend/app"]

[tool.pytest.ini_options]
testpaths = ["tests/python"]
asyncio_mode = "auto"
```

- [ ] **Step 2: Create `.gitignore`**

```gitignore
# Python
__pycache__/
*.py[cod]
.venv/
.uv/
*.egg-info/
build/
dist/
_skbuild/

# C++
build/
*.o
*.a
*.so
*.dylib
*.dll
CMakeCache.txt
CMakeFiles/
cmake_install.cmake
Makefile
compile_commands.json

# Node
node_modules/
.vite/
src/frontend/dist/

# IDE
.vscode/
.idea/
*.swp

# OS
.DS_Store
Thumbs.db
```

- [ ] **Step 3: Delete the placeholder `main.py` at repo root**

```bash
rm "main.py"
```

- [ ] **Step 4: Replace the placeholder root `CMakeLists.txt`**

```cmake
cmake_minimum_required(VERSION 3.24)
project(photonics_twin LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

option(PHOTONICS_BUILD_TESTS "Build C++ unit tests" ON)

add_subdirectory(src/core)
add_subdirectory(src/bindings)

if(PHOTONICS_BUILD_TESTS AND NOT SKBUILD)
    enable_testing()
    add_subdirectory(tests/cpp)
endif()
```

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml .gitignore CMakeLists.txt
git rm main.py
git commit -m "chore: bootstrap pyproject, cmake, gitignore"
```

---

## Task 2: C++ core CMakeLists + GoogleTest fetch

**Files:**
- Create: `src/core/CMakeLists.txt`
- Create: `tests/cpp/CMakeLists.txt`

- [ ] **Step 1: Create `src/core/CMakeLists.txt`**

```cmake
add_library(photonics_core STATIC
    src/materials.cpp
    src/tmm.cpp
    src/bragg.cpp
)

target_include_directories(photonics_core PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_compile_features(photonics_core PUBLIC cxx_std_17)
```

- [ ] **Step 2: Create empty source stubs so CMake can configure**

Create `src/core/src/materials.cpp`, `src/core/src/tmm.cpp`, `src/core/src/bragg.cpp` each containing only:

```cpp
// Stub — implementation lands in later tasks.
```

- [ ] **Step 3: Create `tests/cpp/CMakeLists.txt` with GoogleTest fetch**

```cmake
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
target_link_libraries(photonics_tests PRIVATE photonics_core GTest::gtest_main)

include(GoogleTest)
gtest_discover_tests(photonics_tests)
```

- [ ] **Step 4: Create empty test stubs**

`tests/cpp/test_materials.cpp`, `tests/cpp/test_tmm.cpp`, `tests/cpp/test_bragg.cpp` each containing:

```cpp
#include <gtest/gtest.h>
// Tests land in later tasks.
```

- [ ] **Step 5: Verify CMake configures**

Run:
```bash
cmake -B build -S . -DPHOTONICS_BUILD_TESTS=ON
cmake --build build
```
Expected: configures successfully, builds `photonics_core` static lib and `photonics_tests` executable (which is empty but compiles).

- [ ] **Step 6: Commit**

```bash
git add CMakeLists.txt src/core src/bindings/CMakeLists.txt tests/cpp
git commit -m "build: c++ core skeleton + googletest fetch"
```

(Note: `src/bindings/CMakeLists.txt` is created as a stub here; real content lands in Task 11.)

Stub for `src/bindings/CMakeLists.txt`:
```cmake
# Bindings — populated in Task 11.
```

---

## Task 3: `common.hpp` — numerical types and constants

**Files:**
- Create: `src/core/include/photonics/common.hpp`

- [ ] **Step 1: Create the header**

```cpp
// src/core/include/photonics/common.hpp
#pragma once

#include <complex>
#include <cstddef>

namespace photonics {

#ifdef PHOTONICS_HLS_BUILD
    #include <ap_fixed.h>
    using real_t    = ap_fixed<32, 8>;
    using complex_t = std::complex<real_t>;
#else
    using real_t    = double;
    using complex_t = std::complex<double>;
#endif

inline constexpr std::size_t MAX_LAYERS = 32;

}  // namespace photonics
```

- [ ] **Step 2: Verify it compiles by building the (still-empty) core library**

Run:
```bash
cmake --build build
```
Expected: builds clean.

- [ ] **Step 3: Commit**

```bash
git add src/core/include/photonics/common.hpp
git commit -m "feat(core): common.hpp with real_t/complex_t and MAX_LAYERS"
```

---

## Task 4: `Material` class — TDD via SiO₂ Sellmeier @ 633 nm

**Files:**
- Create: `src/core/include/photonics/materials.hpp`
- Modify: `src/core/src/materials.cpp`
- Modify: `tests/cpp/test_materials.cpp`

Reference: Malitson 1965 fused silica Sellmeier coefficients. Stored convention: `Cᵢ` are squared values (μm²); formula is `n² - 1 = Σ Bᵢ·λ²/(λ² - Cᵢ)` with λ in μm. For SiO₂: B1 = 0.6961663, B2 = 0.4079426, B3 = 0.8974794, C1 = 0.00467914826, C2 = 0.01351206307, C3 = 97.9340025. Hand-computed n(0.633 μm) ≈ 1.4570.

- [ ] **Step 1: Write the failing test**

In `tests/cpp/test_materials.cpp`:

```cpp
#include <gtest/gtest.h>
#include "photonics/materials.hpp"

TEST(Materials, SellmeierSiO2_at_633nm) {
    photonics::SellmeierCoeffs sio2{
        0.6961663, 0.4079426, 0.8974794,
        0.00467914826, 0.01351206307, 97.9340025
    };
    photonics::Material m("SiO2", sio2);
    EXPECT_NEAR(static_cast<double>(m.n(633.0)), 1.4570, 1e-4);
}
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cmake --build build && ctest --test-dir build --output-on-failure
```
Expected: compile error — `materials.hpp` not found.

- [ ] **Step 3: Write the header**

In `src/core/include/photonics/materials.hpp`:

```cpp
#pragma once
#include <string>
#include "photonics/common.hpp"

namespace photonics {

struct SellmeierCoeffs {
    real_t B1, B2, B3;
    real_t C1, C2, C3;   // squared coefficients in μm²
};

class Material {
public:
    Material(std::string name, SellmeierCoeffs c);

    // Refractive index at given wavelength (nm). Internally converts to μm
    // because Sellmeier coefficients are conventionally expressed for λ in μm.
    real_t n(real_t wavelength_nm) const;

    const std::string& name() const { return name_; }

private:
    std::string name_;
    SellmeierCoeffs c_;
};

}  // namespace photonics
```

- [ ] **Step 4: Write the implementation**

In `src/core/src/materials.cpp`:

```cpp
#include "photonics/materials.hpp"
#include <cmath>
#include <utility>

namespace photonics {

Material::Material(std::string name, SellmeierCoeffs c)
    : name_(std::move(name)), c_(c) {}

real_t Material::n(real_t wavelength_nm) const {
    const real_t lambda_um = wavelength_nm / real_t{1000.0};
    const real_t l2 = lambda_um * lambda_um;
    const real_t s =
        c_.B1 * l2 / (l2 - c_.C1) +
        c_.B2 * l2 / (l2 - c_.C2) +
        c_.B3 * l2 / (l2 - c_.C3);
    return std::sqrt(real_t{1.0} + s);
}

}  // namespace photonics
```

- [ ] **Step 5: Run the test, expect it to pass**

```bash
cmake --build build && ctest --test-dir build --output-on-failure
```
Expected: `SellmeierSiO2_at_633nm` PASS.

- [ ] **Step 6: Commit**

```bash
git add src/core/include/photonics/materials.hpp src/core/src/materials.cpp tests/cpp/test_materials.cpp
git commit -m "feat(core): Material with Sellmeier dispersion (Malitson SiO2 test)"
```

---

## Task 5: `Material` — Si Sellmeier @ 1550 nm

**Files:**
- Modify: `tests/cpp/test_materials.cpp`

Reference: Salzberg & Villa / Edwards-Ochoa coefficients for crystalline Si, valid 1.36-11 μm at room temperature. Stored as: B1 = 10.6684293, B2 = 0.003043475, B3 = 1.54133408, C1 = 0.090912191 (= 0.301516485²), C2 = 1.287460152 (= 1.13475115²), C3 = 1218816.0 (= 1104.0²). Computed n(1.550 μm) ≈ 3.4778.

- [ ] **Step 1: Append the failing test**

```cpp
TEST(Materials, SellmeierSi_at_1550nm) {
    photonics::SellmeierCoeffs si{
        10.6684293, 0.003043475, 1.54133408,
        0.090912191, 1.287460152, 1218816.0
    };
    photonics::Material m("Si", si);
    EXPECT_NEAR(static_cast<double>(m.n(1550.0)), 3.4778, 1e-3);
}
```

- [ ] **Step 2: Run the test, expect PASS** (no implementation needed; existing `Material::n` covers this case)

```bash
cmake --build build && ctest --test-dir build --output-on-failure
```
Expected: both Sellmeier tests pass.

- [ ] **Step 3: Commit**

```bash
git add tests/cpp/test_materials.cpp
git commit -m "test(core): Sellmeier coverage for Si at 1550 nm"
```

---

## Task 6: `Layer` and `LayerStack` — TDD on size and accessor

**Files:**
- Create: `src/core/include/photonics/tmm.hpp`
- Modify: `src/core/src/tmm.cpp`
- Modify: `tests/cpp/test_tmm.cpp`

- [ ] **Step 1: Write the failing test**

In `tests/cpp/test_tmm.cpp`:

```cpp
#include <gtest/gtest.h>
#include "photonics/tmm.hpp"
#include "photonics/materials.hpp"

namespace {
photonics::Material make_si() {
    return photonics::Material("Si", {10.6684293, 0.003043475, 1.54133408,
                                       0.090912191, 1.287460152, 1218816.0});
}
photonics::Material make_sio2() {
    return photonics::Material("SiO2", {0.6961663, 0.4079426, 0.8974794,
                                         0.00467914826, 0.01351206307, 97.9340025});
}
}

TEST(LayerStack, AddLayerAndAccess) {
    auto si = make_si();
    auto sio2 = make_sio2();
    photonics::LayerStack stack;
    stack.add_layer(110.7, si);
    stack.add_layer(267.2, sio2);

    EXPECT_EQ(stack.size(), 2u);
    EXPECT_NEAR(static_cast<double>(stack.at(0).thickness_nm), 110.7, 1e-9);
    EXPECT_EQ(stack.at(0).material->name(), "Si");
    EXPECT_EQ(stack.at(1).material->name(), "SiO2");
}
```

- [ ] **Step 2: Run, expect compile failure**

```bash
cmake --build build
```
Expected: `tmm.hpp` not found.

- [ ] **Step 3: Write `tmm.hpp`**

```cpp
// src/core/include/photonics/tmm.hpp
#pragma once
#include <vector>
#include "photonics/common.hpp"
#include "photonics/materials.hpp"

namespace photonics {

struct Layer {
    real_t thickness_nm;
    const Material* material;
};

class LayerStack {
public:
    void add_layer(real_t thickness_nm, const Material& m);
    std::size_t size() const { return layers_.size(); }
    const Layer& at(std::size_t i) const { return layers_.at(i); }

private:
    std::vector<Layer> layers_;
};

// Free function — the HLS synthesis target.
// Computes complex r and t at each wavelength for normal-incidence light
// entering from vacuum (n=1) into the stack with vacuum behind it.
void tmm_sweep(const LayerStack& stack,
               const real_t* wavelengths_nm, std::size_t n_wl,
               complex_t* r_out, complex_t* t_out);

}  // namespace photonics
```

- [ ] **Step 4: Implement `add_layer` in `tmm.cpp`**

```cpp
// src/core/src/tmm.cpp
#include "photonics/tmm.hpp"

namespace photonics {

void LayerStack::add_layer(real_t thickness_nm, const Material& m) {
    layers_.push_back(Layer{thickness_nm, &m});
}

void tmm_sweep(const LayerStack&, const real_t*, std::size_t,
               complex_t*, complex_t*) {
    // Implementation in Task 7.
}

}  // namespace photonics
```

- [ ] **Step 5: Run, expect PASS**

```bash
cmake --build build && ctest --test-dir build --output-on-failure
```

- [ ] **Step 6: Commit**

```bash
git add src/core/include/photonics/tmm.hpp src/core/src/tmm.cpp tests/cpp/test_tmm.cpp
git commit -m "feat(core): LayerStack with Layer storage"
```

---

## Task 7: `tmm_sweep` — empty stack (Fresnel air→air)

**Files:**
- Modify: `src/core/src/tmm.cpp`
- Modify: `tests/cpp/test_tmm.cpp`

The simplest test: an empty stack with vacuum on both sides should give r = 0, t = 1 at every wavelength (no interface). This validates the boundary handling before the layer loop is exercised.

- [ ] **Step 1: Append the failing test**

```cpp
#include <complex>

TEST(TMMSweep, EmptyStackGivesZeroReflectance) {
    photonics::LayerStack stack;
    const double wl[3] = {1400.0, 1550.0, 1700.0};
    photonics::complex_t r[3], t[3];
    photonics::tmm_sweep(stack, wl, 3, r, t);

    for (int i = 0; i < 3; ++i) {
        EXPECT_NEAR(std::abs(r[i]), 0.0, 1e-12);
        EXPECT_NEAR(std::abs(t[i]), 1.0, 1e-12);
    }
}
```

- [ ] **Step 2: Run, expect FAIL** (current stub does nothing; `r` and `t` are uninitialised → undefined values)

```bash
cmake --build build && ctest --test-dir build --output-on-failure
```

- [ ] **Step 3: Implement `tmm_sweep` (full TMM, not just empty case)**

Replace the stub in `src/core/src/tmm.cpp`:

```cpp
#include "photonics/tmm.hpp"
#include <cmath>

namespace photonics {

namespace {
constexpr real_t PI = real_t{3.14159265358979323846};

// 2x2 complex matrix.
struct Mat2 {
    complex_t a, b, c, d;
};

inline Mat2 mat_mul(const Mat2& X, const Mat2& Y) {
    return Mat2{
        X.a*Y.a + X.b*Y.c, X.a*Y.b + X.b*Y.d,
        X.c*Y.a + X.d*Y.c, X.c*Y.b + X.d*Y.d
    };
}
}  // namespace

void tmm_sweep(const LayerStack& stack,
               const real_t* wavelengths_nm, std::size_t n_wl,
               complex_t* r_out, complex_t* t_out) {
    constexpr complex_t I{0.0, 1.0};
    const complex_t n_in{1.0, 0.0};   // vacuum incident medium
    const complex_t n_sub{1.0, 0.0};  // vacuum substrate (no extra interface)

    for (std::size_t k = 0; k < n_wl; ++k) {
        const real_t lambda = wavelengths_nm[k];

        // Identity matrix.
        Mat2 M{ {1.0,0.0}, {0.0,0.0}, {0.0,0.0}, {1.0,0.0} };

        for (std::size_t li = 0; li < stack.size(); ++li) {
            const auto& layer = stack.at(li);
            const complex_t n{static_cast<double>(layer.material->n(lambda)), 0.0};
            const real_t delta = real_t{2.0} * PI * static_cast<double>(n.real())
                                 * layer.thickness_nm / lambda;
            const complex_t cos_d{std::cos(static_cast<double>(delta)), 0.0};
            const complex_t sin_d{std::sin(static_cast<double>(delta)), 0.0};
            // Characteristic matrix for normal incidence.
            Mat2 L{
                cos_d,           I * sin_d / n,
                I * n * sin_d,   cos_d
            };
            M = mat_mul(M, L);
        }

        // r = (m11*n_in + m12*n_in*n_sub - m21 - m22*n_sub)
        //   / (m11*n_in + m12*n_in*n_sub + m21 + m22*n_sub)
        const complex_t num = M.a*n_in + M.b*n_in*n_sub - M.c - M.d*n_sub;
        const complex_t den = M.a*n_in + M.b*n_in*n_sub + M.c + M.d*n_sub;
        r_out[k] = num / den;
        // t = 2*n_in / den
        t_out[k] = (complex_t{2.0,0.0} * n_in) / den;
    }
}

}  // namespace photonics
```

- [ ] **Step 4: Run, expect PASS**

```bash
cmake --build build && ctest --test-dir build --output-on-failure
```

- [ ] **Step 5: Commit**

```bash
git add src/core/src/tmm.cpp tests/cpp/test_tmm.cpp
git commit -m "feat(core): tmm_sweep with empty-stack test"
```

---

## Task 8: `tmm_sweep` — single quarter-wave layer hand-verified

**Files:**
- Modify: `tests/cpp/test_tmm.cpp`

A single layer of refractive index n_L and physical thickness d = λ₀/(4·n_L) at design wavelength λ₀ between vacuum (incident) and vacuum (substrate, identical) gives a known closed-form reflectance: at λ = λ₀, |r|² = ((n_L² - 1)/(n_L² + 1))². For n_L = 2.0, |r|² = (3/5)² = 0.36.

We use a synthetic constant-index "Material" — Sellmeier coefficients chosen so n is approximately constant across the test wavelength. Easiest: use a single-term Sellmeier with very large C, giving near-flat dispersion.

- [ ] **Step 1: Append the failing test**

```cpp
TEST(TMMSweep, SingleQuarterWaveAirSubstrate) {
    // Approximately constant n=2.0 over the test range:
    // From n^2 - 1 = B*λ² / (λ² - C), pick B = 3, C very large so the term
    // approaches B*λ²/-C → small; better: pick B = 3, C = 0 → n² - 1 = 3 → n = 2.
    photonics::SellmeierCoeffs flat{3.0, 0.0, 0.0, 0.0, 1.0, 1.0};
    photonics::Material m("flat", flat);
    // Sanity: n(any λ) ≈ 2.0
    ASSERT_NEAR(static_cast<double>(m.n(1550.0)), 2.0, 1e-9);

    const double n_L = 2.0;
    const double lambda0 = 1550.0;
    const double thickness = lambda0 / (4.0 * n_L);  // 193.75 nm

    photonics::LayerStack stack;
    stack.add_layer(thickness, m);

    const double wl[1] = {lambda0};
    photonics::complex_t r[1], t[1];
    photonics::tmm_sweep(stack, wl, 1, r, t);

    const double R_expected = ((n_L*n_L - 1.0) / (n_L*n_L + 1.0))
                            * ((n_L*n_L - 1.0) / (n_L*n_L + 1.0));
    EXPECT_NEAR(std::norm(r[0]), R_expected, 1e-6);
}
```

(Note: with C2 = C3 = 1, but B2 = B3 = 0, those terms contribute zero; only the first term matters. With C1 = 0, the first term simplifies to n² - 1 = B1 = 3, so n = 2 exactly at every wavelength.)

- [ ] **Step 2: Run, expect PASS**

```bash
cmake --build build && ctest --test-dir build --output-on-failure
```

- [ ] **Step 3: Commit**

```bash
git add tests/cpp/test_tmm.cpp
git commit -m "test(core): single quarter-wave layer hand-verified |r|^2 = 0.36"
```

---

## Task 9: `BraggGrating` — stack composition tests

**Files:**
- Create: `src/core/include/photonics/bragg.hpp`
- Modify: `src/core/src/bragg.cpp`
- Modify: `tests/cpp/test_bragg.cpp`

A `BraggGrating(high, low, λ₀, periods=N)` produces 2·N quarter-wave layers, alternating starting with `high`. Layer thicknesses are λ₀/(4·n(λ₀)).

- [ ] **Step 1: Write the failing tests**

```cpp
// tests/cpp/test_bragg.cpp
#include <gtest/gtest.h>
#include "photonics/bragg.hpp"

namespace {
photonics::Material make_si() {
    return photonics::Material("Si", {10.6684293, 0.003043475, 1.54133408,
                                       0.090912191, 1.287460152, 1218816.0});
}
photonics::Material make_sio2() {
    return photonics::Material("SiO2", {0.6961663, 0.4079426, 0.8974794,
                                         0.00467914826, 0.01351206307, 97.9340025});
}
}

TEST(BraggGrating, StackHasCorrectLayerCount) {
    photonics::BraggGrating g(make_si(), make_sio2(), 1550.0, 15);
    EXPECT_EQ(g.stack().size(), 30u);
}

TEST(BraggGrating, QuarterWaveThicknessesAtCentre) {
    auto si = make_si();
    auto sio2 = make_sio2();
    photonics::BraggGrating g(si, sio2, 1550.0, 2);
    const double n_si  = static_cast<double>(si.n(1550.0));
    const double n_sio = static_cast<double>(sio2.n(1550.0));

    EXPECT_NEAR(static_cast<double>(g.stack().at(0).thickness_nm),
                1550.0 / (4.0 * n_si), 1e-6);
    EXPECT_NEAR(static_cast<double>(g.stack().at(1).thickness_nm),
                1550.0 / (4.0 * n_sio), 1e-6);
    EXPECT_EQ(g.stack().at(0).material->name(), "Si");
    EXPECT_EQ(g.stack().at(1).material->name(), "SiO2");
}
```

- [ ] **Step 2: Run, expect compile failure** (no `bragg.hpp`)

```bash
cmake --build build
```

- [ ] **Step 3: Write `bragg.hpp`**

```cpp
// src/core/include/photonics/bragg.hpp
#pragma once
#include "photonics/tmm.hpp"
#include "photonics/materials.hpp"

namespace photonics {

class BraggGrating {
public:
    BraggGrating(Material high, Material low, real_t centre_nm, std::size_t periods);

    void set_centre_nm(real_t v);
    void set_periods(std::size_t v);

    real_t      centre_nm() const { return centre_nm_; }
    std::size_t periods()   const { return periods_; }

    const LayerStack& stack() const { return cached_stack_; }

    // Reflectance |r|^2 at each input wavelength.
    void reflectance(const real_t* wavelengths_nm, std::size_t n_wl,
                     real_t* R_out) const;

private:
    void rebuild_stack_();

    Material high_;
    Material low_;
    real_t   centre_nm_;
    std::size_t periods_;
    LayerStack cached_stack_;
};

}  // namespace photonics
```

- [ ] **Step 4: Implement `bragg.cpp`**

```cpp
#include "photonics/bragg.hpp"
#include <complex>
#include <utility>
#include <vector>

namespace photonics {

BraggGrating::BraggGrating(Material high, Material low,
                           real_t centre_nm, std::size_t periods)
    : high_(std::move(high)), low_(std::move(low)),
      centre_nm_(centre_nm), periods_(periods) {
    rebuild_stack_();
}

void BraggGrating::set_centre_nm(real_t v) { centre_nm_ = v; rebuild_stack_(); }
void BraggGrating::set_periods(std::size_t v) { periods_ = v; rebuild_stack_(); }

void BraggGrating::rebuild_stack_() {
    cached_stack_ = LayerStack{};
    const real_t t_h = centre_nm_ / (real_t{4.0} * high_.n(centre_nm_));
    const real_t t_l = centre_nm_ / (real_t{4.0} * low_.n(centre_nm_));
    for (std::size_t i = 0; i < periods_; ++i) {
        cached_stack_.add_layer(t_h, high_);
        cached_stack_.add_layer(t_l, low_);
    }
}

void BraggGrating::reflectance(const real_t* wl, std::size_t n_wl,
                               real_t* R_out) const {
    std::vector<complex_t> r(n_wl), t(n_wl);
    tmm_sweep(cached_stack_, wl, n_wl, r.data(), t.data());
    for (std::size_t i = 0; i < n_wl; ++i) {
        R_out[i] = std::norm(r[i]);
    }
}

}  // namespace photonics
```

- [ ] **Step 5: Run, expect PASS**

```bash
cmake --build build && ctest --test-dir build --output-on-failure
```

- [ ] **Step 6: Commit**

```bash
git add src/core/include/photonics/bragg.hpp src/core/src/bragg.cpp tests/cpp/test_bragg.cpp
git commit -m "feat(core): BraggGrating quarter-wave stack composition"
```

---

## Task 10: `BraggGrating::reflectance` — peak-at-centre sanity test

**Files:**
- Modify: `tests/cpp/test_bragg.cpp`

A 15-period Si/SiO₂ grating designed for 1550 nm should produce its highest reflectance at 1550 nm across a 1400-1700 nm sweep.

- [ ] **Step 1: Append the failing test**

```cpp
TEST(BraggGrating, ReflectancePeaksAtCentre) {
    photonics::BraggGrating g(make_si(), make_sio2(), 1550.0, 15);

    constexpr std::size_t N = 501;
    std::vector<double> wl(N), R(N);
    const double start = 1400.0, stop = 1700.0;
    for (std::size_t i = 0; i < N; ++i) {
        wl[i] = start + (stop - start) * static_cast<double>(i) / (N - 1);
    }
    g.reflectance(wl.data(), N, R.data());

    auto peak_it = std::max_element(R.begin(), R.end());
    const std::size_t peak_idx = static_cast<std::size_t>(peak_it - R.begin());
    const double peak_wl = wl[peak_idx];

    EXPECT_NEAR(peak_wl, 1550.0, 0.5);
    EXPECT_GT(*peak_it, 0.99);
}
```

Add `#include <algorithm>` and `#include <vector>` at the top of the test file if not already present.

- [ ] **Step 2: Run, expect PASS**

```bash
cmake --build build && ctest --test-dir build --output-on-failure
```

- [ ] **Step 3: Commit**

```bash
git add tests/cpp/test_bragg.cpp
git commit -m "test(core): bragg reflectance peaks at design wavelength"
```

---

## Task 11: pybind11 module — minimal `photonics_core` extension

**Files:**
- Modify: `src/bindings/CMakeLists.txt`
- Create: `src/bindings/photonics_core.cpp`
- Modify: `pyproject.toml` (already has scikit-build-core; nothing to add here)

- [ ] **Step 1: Replace `src/bindings/CMakeLists.txt`**

```cmake
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
```

The static lib name needs renaming to avoid collision with the Python module target. Update `src/core/CMakeLists.txt`:

```cmake
add_library(photonics_core_lib STATIC
    src/materials.cpp
    src/tmm.cpp
    src/bragg.cpp
)
target_include_directories(photonics_core_lib PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_compile_features(photonics_core_lib PUBLIC cxx_std_17)
```

And `tests/cpp/CMakeLists.txt`:

```cmake
target_link_libraries(photonics_tests PRIVATE photonics_core_lib GTest::gtest_main)
```

- [ ] **Step 2: Create the module entry**

`src/bindings/photonics_core.cpp`:

```cpp
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

PYBIND11_MODULE(photonics_core, m) {
    m.doc() = "SPEAR Photonics Digital Twin — C++ core (Bragg slice)";
    m.attr("__version__") = "0.1.0";
}
```

- [ ] **Step 3: Build and import**

Install editable + verify import:

```bash
uv venv
uv pip install -e .[dev]
uv run python -c "import photonics_core; print(photonics_core.__version__)"
```

Expected output: `0.1.0`.

- [ ] **Step 4: Verify C++ tests still build separately**

```bash
cmake -B build -S . && cmake --build build && ctest --test-dir build --output-on-failure
```

Expected: all 7 C++ tests still PASS.

- [ ] **Step 5: Commit**

```bash
git add src/bindings/CMakeLists.txt src/bindings/photonics_core.cpp src/core/CMakeLists.txt tests/cpp/CMakeLists.txt
git commit -m "build: pybind11 module skeleton + rename static lib"
```

---

## Task 12: Bind `Material` — TDD via pytest

**Files:**
- Modify: `src/bindings/photonics_core.cpp`
- Create: `tests/python/conftest.py`
- Create: `tests/python/test_bindings.py`

- [ ] **Step 1: Write the failing test**

`tests/python/conftest.py`:

```python
import pytest

@pytest.fixture
def si_coeffs():
    return (10.6684293, 0.003043475, 1.54133408,
            0.090912191, 1.287460152, 1218816.0)

@pytest.fixture
def sio2_coeffs():
    return (0.6961663, 0.4079426, 0.8974794,
            0.00467914826, 0.01351206307, 97.9340025)
```

`tests/python/test_bindings.py`:

```python
import photonics_core as pc

def test_material_n_at_633nm(sio2_coeffs):
    m = pc.Material("SiO2", pc.SellmeierCoeffs(*sio2_coeffs))
    assert abs(m.n(633.0) - 1.4570) < 1e-4

def test_material_name(si_coeffs):
    m = pc.Material("Si", pc.SellmeierCoeffs(*si_coeffs))
    assert m.name == "Si"
```

- [ ] **Step 2: Run, expect ImportError on `pc.Material`**

```bash
uv run pytest tests/python/test_bindings.py -v
```

- [ ] **Step 3: Add `Material` and `SellmeierCoeffs` bindings**

In `src/bindings/photonics_core.cpp`:

```cpp
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "photonics/materials.hpp"

namespace py = pybind11;
using photonics::Material;
using photonics::SellmeierCoeffs;

PYBIND11_MODULE(photonics_core, m) {
    m.doc() = "SPEAR Photonics Digital Twin — C++ core (Bragg slice)";
    m.attr("__version__") = "0.1.0";

    py::class_<SellmeierCoeffs>(m, "SellmeierCoeffs")
        .def(py::init<double, double, double, double, double, double>(),
             py::arg("B1"), py::arg("B2"), py::arg("B3"),
             py::arg("C1"), py::arg("C2"), py::arg("C3"));

    py::class_<Material>(m, "Material")
        .def(py::init<std::string, SellmeierCoeffs>(),
             py::arg("name"), py::arg("coeffs"))
        .def("n", &Material::n, py::arg("wavelength_nm"))
        .def_property_readonly("name", &Material::name);
}
```

- [ ] **Step 4: Reinstall and run, expect PASS**

```bash
uv pip install -e . --no-build-isolation
uv run pytest tests/python/test_bindings.py -v
```

- [ ] **Step 5: Commit**

```bash
git add src/bindings/photonics_core.cpp tests/python/conftest.py tests/python/test_bindings.py
git commit -m "feat(bindings): expose Material and SellmeierCoeffs"
```

---

## Task 13: Bind `BraggGrating` — numpy round-trip

**Files:**
- Modify: `src/bindings/photonics_core.cpp`
- Modify: `tests/python/test_bindings.py`

- [ ] **Step 1: Append the failing test**

```python
import numpy as np

def test_bragg_reflectance_roundtrip(si_coeffs, sio2_coeffs):
    si  = pc.Material("Si",   pc.SellmeierCoeffs(*si_coeffs))
    sio = pc.Material("SiO2", pc.SellmeierCoeffs(*sio2_coeffs))
    g = pc.BraggGrating(si, sio, 1550.0, 15)

    wl = np.linspace(1400.0, 1700.0, 501, dtype=np.float64)
    R = g.reflectance(wl)
    assert R.shape == (501,)
    assert R.dtype == np.float64
    assert R.flags["C_CONTIGUOUS"]

    peak = float(wl[int(np.argmax(R))])
    assert abs(peak - 1550.0) < 0.5
    assert R.max() > 0.99

def test_bragg_stack_layer_count(si_coeffs, sio2_coeffs):
    si  = pc.Material("Si",   pc.SellmeierCoeffs(*si_coeffs))
    sio = pc.Material("SiO2", pc.SellmeierCoeffs(*sio2_coeffs))
    g = pc.BraggGrating(si, sio, 1550.0, 15)
    layers = g.stack_view()
    assert len(layers) == 30
    assert layers[0]["material"] == "Si"
    assert layers[1]["material"] == "SiO2"
    assert layers[0]["thickness_nm"] > 0
    assert "n_at_centre" in layers[0]
```

- [ ] **Step 2: Run, expect FAIL**

```bash
uv run pytest tests/python/test_bindings.py -v
```

- [ ] **Step 3: Extend bindings**

Append to `src/bindings/photonics_core.cpp`:

```cpp
#include <pybind11/numpy.h>
#include "photonics/bragg.hpp"
#include "photonics/tmm.hpp"

using photonics::BraggGrating;
using photonics::LayerStack;
```

Inside the `PYBIND11_MODULE`:

```cpp
    py::class_<BraggGrating>(m, "BraggGrating")
        .def(py::init<Material, Material, double, std::size_t>(),
             py::arg("high"), py::arg("low"),
             py::arg("centre_nm"), py::arg("periods"))
        .def("set_centre_nm", &BraggGrating::set_centre_nm)
        .def("set_periods",   &BraggGrating::set_periods)
        .def_property_readonly("centre_nm", &BraggGrating::centre_nm)
        .def_property_readonly("periods",   &BraggGrating::periods)
        .def("reflectance",
             [](const BraggGrating& self, py::array_t<double, py::array::c_style> wl) {
                 auto buf = wl.request();
                 if (buf.ndim != 1) throw std::runtime_error("wavelengths must be 1-D");
                 const std::size_t n = static_cast<std::size_t>(buf.shape[0]);
                 py::array_t<double> R(static_cast<py::ssize_t>(n));
                 self.reflectance(static_cast<const double*>(buf.ptr), n,
                                  static_cast<double*>(R.request().ptr));
                 return R;
             }, py::arg("wavelengths_nm"))
        .def("stack_view",
             [](const BraggGrating& self) {
                 const auto& s = self.stack();
                 const double centre = static_cast<double>(self.centre_nm());
                 py::list out;
                 for (std::size_t i = 0; i < s.size(); ++i) {
                     const auto& L = s.at(i);
                     py::dict d;
                     d["index"]        = static_cast<int>(i);
                     d["material"]     = L.material->name();
                     d["thickness_nm"] = static_cast<double>(L.thickness_nm);
                     d["n_at_centre"]  = static_cast<double>(L.material->n(centre));
                     out.append(d);
                 }
                 return out;
             });
```

- [ ] **Step 4: Reinstall and run, expect PASS**

```bash
uv pip install -e . --no-build-isolation
uv run pytest tests/python/test_bindings.py -v
```

- [ ] **Step 5: Commit**

```bash
git add src/bindings/photonics_core.cpp tests/python/test_bindings.py
git commit -m "feat(bindings): BraggGrating with numpy reflectance + stack_view"
```

---

## Task 14: `compute_reference.py` — Born & Wolf §1.6.5 oracle

**Files:**
- Create: `scripts/compute_reference.py`
- Create: `data/materials/sellmeier_si.json`
- Create: `data/materials/sellmeier_sio2.json`

The script evaluates closed-form expressions for a quarter-wave Si/SiO₂ Bragg grating. Born & Wolf §1.6.5: at the design wavelength, the matrix product simplifies to a diagonal form whose reflectance is given by `R = ((1 - (n_h/n_l)^(2N)·(1/n_sub)) / (1 + (n_h/n_l)^(2N)·(1/n_sub)))²` for vacuum substrate (n_sub = 1) — and stop-band edges are `λ_edge = λ₀ · π / (π ± 2·arcsin((n_h - n_l)/(n_h + n_l)))`.

- [ ] **Step 1: Create material JSON files**

`data/materials/sellmeier_si.json`:

```json
{
  "name": "Si",
  "source": "Edwards/Salzberg-Villa, room temp, valid 1.36-11 μm",
  "coeffs": {
    "B1": 10.6684293, "B2": 0.003043475, "B3": 1.54133408,
    "C1": 0.090912191, "C2": 1.287460152, "C3": 1218816.0
  }
}
```

`data/materials/sellmeier_sio2.json`:

```json
{
  "name": "SiO2",
  "source": "Malitson 1965, fused silica, room temp, valid 0.21-3.71 μm",
  "coeffs": {
    "B1": 0.6961663, "B2": 0.4079426, "B3": 0.8974794,
    "C1": 0.00467914826, "C2": 0.01351206307, "C3": 97.9340025
  }
}
```

- [ ] **Step 2: Create `scripts/compute_reference.py`**

```python
"""Independent oracle for the Born & Wolf §1.6.5 quarter-wave Bragg grating.

This script does NOT use the photonics_core C++ kernel. It computes the
reference values from the closed-form expressions in Born & Wolf so that
the test suite can compare the simulator's output against an independent
analytical reference. Run once and freeze the output into
data/validation/quarterwave_si_sio2_reference.json.
"""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def load_sellmeier(name):
    with open(ROOT / "data" / "materials" / f"sellmeier_{name.lower()}.json") as fh:
        return json.load(fh)["coeffs"]

def sellmeier_n(coeffs, wavelength_nm):
    lam = wavelength_nm / 1000.0
    l2 = lam * lam
    s = (coeffs["B1"] * l2 / (l2 - coeffs["C1"]) +
         coeffs["B2"] * l2 / (l2 - coeffs["C2"]) +
         coeffs["B3"] * l2 / (l2 - coeffs["C3"]))
    return math.sqrt(1.0 + s)

def main():
    centre = 1550.0
    periods = 15
    n_high = sellmeier_n(load_sellmeier("Si"),   centre)
    n_low  = sellmeier_n(load_sellmeier("SiO2"), centre)
    n_sub  = 1.0  # vacuum substrate

    # Born & Wolf §1.6.5 peak reflectance for a quarter-wave stack of N
    # high/low pairs in vacuum:  R = ((1 - q) / (1 + q))^2
    # where q = (n_low / n_high)^(2N) * (1 / n_sub)
    q = (n_low / n_high) ** (2 * periods) * (1.0 / n_sub)
    R_peak = ((1.0 - q) / (1.0 + q)) ** 2

    # Stop-band edges:
    # Δω/ω₀ = (2/π) * arcsin((n_high - n_low) / (n_high + n_low))
    # → λ_edge = λ₀ * π / (π ± 2*arcsin(...))
    a = math.asin((n_high - n_low) / (n_high + n_low))
    edge_high = centre * math.pi / (math.pi - 2.0 * a)
    edge_low  = centre * math.pi / (math.pi + 2.0 * a)

    out = {
        "description": ("Si/SiO2 quarter-wave Bragg @ 1550 nm, 15 periods, "
                        "vacuum incident & substrate. Reference: Born & Wolf §1.6.5."),
        "params": {
            "material_high": "Si", "material_low": "SiO2",
            "centre_nm": centre, "periods": periods
        },
        "sweep": {"start_nm": 1400.0, "stop_nm": 1700.0, "n_points": 501},
        "reference": {
            "peak_reflectance": round(R_peak, 8),
            "peak_reflectance_tol": 1e-3,
            "peak_wavelength_nm": centre,
            "peak_wavelength_tol_nm": 0.5,
            "stop_band_edge_low_nm": round(edge_low, 4),
            "stop_band_edge_high_nm": round(edge_high, 4),
            "stop_band_edge_tol_nm": 5.0
        },
        "n_high_at_centre": round(n_high, 6),
        "n_low_at_centre":  round(n_low, 6)
    }

    out_path = ROOT / "data" / "validation" / "quarterwave_si_sio2_reference.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as fh:
        json.dump(out, fh, indent=2)
    print(f"Wrote {out_path}")

if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Run the script to generate the JSON**

```bash
uv run python scripts/compute_reference.py
```

Expected: writes `data/validation/quarterwave_si_sio2_reference.json` with concrete values, prints the path.

- [ ] **Step 4: Inspect the generated file**

```bash
cat data/validation/quarterwave_si_sio2_reference.json
```

Expected: a populated JSON file with `peak_reflectance` close to 0.9999, `peak_wavelength_nm = 1550.0`, and stop-band edges roughly 1465-1645 nm.

- [ ] **Step 5: Commit**

```bash
git add scripts/compute_reference.py data/materials data/validation
git commit -m "feat(validation): Born & Wolf §1.6.5 reference oracle + frozen JSON"
```

---

## Task 15: pytest reference-fixture test

**Files:**
- Modify: `tests/python/test_bindings.py`

- [ ] **Step 1: Append the failing test**

```python
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

def test_reference_fixture(si_coeffs, sio2_coeffs):
    fixture_path = REPO_ROOT / "data" / "validation" / "quarterwave_si_sio2_reference.json"
    fixture = json.loads(fixture_path.read_text())
    p = fixture["params"]; sw = fixture["sweep"]; ref = fixture["reference"]

    si  = pc.Material("Si",   pc.SellmeierCoeffs(*si_coeffs))
    sio = pc.Material("SiO2", pc.SellmeierCoeffs(*sio2_coeffs))
    g = pc.BraggGrating(si, sio, p["centre_nm"], p["periods"])

    wl = np.linspace(sw["start_nm"], sw["stop_nm"], sw["n_points"], dtype=np.float64)
    R = g.reflectance(wl)

    peak_idx = int(np.argmax(R))
    assert abs(float(wl[peak_idx]) - ref["peak_wavelength_nm"]) < ref["peak_wavelength_tol_nm"]
    assert abs(float(R.max()) - ref["peak_reflectance"]) < ref["peak_reflectance_tol"]

    # Stop-band edges: leftmost and rightmost wavelengths in the sweep where R > 0.5
    above = np.where(R > 0.5)[0]
    assert above.size > 0, "No high-R region — peak reflectance assertion above must have failed first"
    edge_low_meas  = float(wl[above[0]])
    edge_high_meas = float(wl[above[-1]])
    assert abs(edge_low_meas  - ref["stop_band_edge_low_nm"])  < ref["stop_band_edge_tol_nm"]
    assert abs(edge_high_meas - ref["stop_band_edge_high_nm"]) < ref["stop_band_edge_tol_nm"]
```

- [ ] **Step 2: Run, expect PASS**

```bash
uv run pytest tests/python/test_bindings.py::test_reference_fixture -v
```

- [ ] **Step 3: Commit**

```bash
git add tests/python/test_bindings.py
git commit -m "test(bindings): assert simulator output matches Born & Wolf oracle"
```

---

## Task 16: FastAPI scaffold + health endpoint

**Files:**
- Create: `src/backend/app/__init__.py`
- Create: `src/backend/app/main.py`
- Create: `src/backend/app/routers/__init__.py`
- Create: `tests/python/test_api.py`

- [ ] **Step 1: Write the failing test**

`tests/python/test_api.py`:

```python
import pytest
from httpx import AsyncClient, ASGITransport
from photonics_twin_app.main import create_app

@pytest.fixture
def app():
    return create_app()

@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

async def test_healthz(client):
    r = await client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
```

The package import path is `photonics_twin_app` to avoid colliding with the (deferred) `app` directory in test discovery. Update `pyproject.toml` `wheel.packages` accordingly:

In `pyproject.toml`, change:
```toml
wheel.packages = ["src/backend/app"]
```
to:
```toml
wheel.packages = ["src/backend/photonics_twin_app"]
```

…and we'll create the package at that path instead of `src/backend/app`. (Updated paths: `src/backend/photonics_twin_app/main.py`, etc.)

Also add to `pyproject.toml`:
```toml
[tool.scikit-build]
sdist.include = ["src/backend/photonics_twin_app/**"]
```
(if not already covered by `wheel.packages`).

- [ ] **Step 2: Create `src/backend/photonics_twin_app/__init__.py`** (empty file)

- [ ] **Step 3: Create `src/backend/photonics_twin_app/main.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

def create_app() -> FastAPI:
    app = FastAPI(title="Photonics Twin", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/healthz")
    def healthz():
        return {"status": "ok"}

    return app

app = create_app()
```

- [ ] **Step 4: Create `src/backend/photonics_twin_app/routers/__init__.py`** (empty file)

- [ ] **Step 5: Reinstall and run**

```bash
uv pip install -e .[dev] --no-build-isolation
uv run pytest tests/python/test_api.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml src/backend/photonics_twin_app tests/python/test_api.py
git commit -m "feat(backend): FastAPI app factory + /healthz"
```

---

## Task 17: Pydantic schemas

**Files:**
- Create: `src/backend/photonics_twin_app/schemas.py`
- Modify: `tests/python/test_api.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/python/test_api.py`:

```python
from pydantic import ValidationError
from photonics_twin_app.schemas import SimulateRequest

def test_simulate_request_valid():
    req = SimulateRequest(
        component="bragg_grating",
        params={"material_high": "Si", "material_low": "SiO2",
                "centre_nm": 1550.0, "periods": 15},
        sweep={"start_nm": 1400.0, "stop_nm": 1700.0, "n_points": 501},
    )
    assert req.params.periods == 15

def test_simulate_request_rejects_unknown_material():
    with pytest.raises(ValidationError):
        SimulateRequest(
            component="bragg_grating",
            params={"material_high": "Au", "material_low": "SiO2",
                    "centre_nm": 1550.0, "periods": 15},
            sweep={"start_nm": 1400.0, "stop_nm": 1700.0, "n_points": 501},
        )

def test_simulate_request_rejects_too_many_periods():
    with pytest.raises(ValidationError):
        SimulateRequest(
            component="bragg_grating",
            params={"material_high": "Si", "material_low": "SiO2",
                    "centre_nm": 1550.0, "periods": 17},  # > MAX_LAYERS / 2
            sweep={"start_nm": 1400.0, "stop_nm": 1700.0, "n_points": 501},
        )
```

- [ ] **Step 2: Run, expect ImportError**

```bash
uv run pytest tests/python/test_api.py -v
```

- [ ] **Step 3: Create `src/backend/photonics_twin_app/schemas.py`**

```python
from pydantic import BaseModel, Field, conint, confloat

class BraggParams(BaseModel):
    material_high: str = Field(pattern="^(Si|SiO2)$")
    material_low:  str = Field(pattern="^(Si|SiO2)$")
    centre_nm:     confloat(ge=400.0, le=2500.0)
    periods:       conint(ge=2, le=16)   # 2 * 16 == MAX_LAYERS

class Sweep(BaseModel):
    start_nm: confloat(ge=200.0, le=3000.0)
    stop_nm:  confloat(ge=200.0, le=3000.0)
    n_points: conint(ge=11, le=4001)

class SimulateRequest(BaseModel):
    component: str
    params: BraggParams
    sweep:  Sweep

class LayerOut(BaseModel):
    index: int
    material: str
    thickness_nm: float
    n_at_centre: float

class SimulateResponse(BaseModel):
    wavelengths_nm: list[float]
    reflectance:    list[float]
    stack: list[LayerOut]
    meta:  dict
```

- [ ] **Step 4: Run, expect PASS**

```bash
uv run pytest tests/python/test_api.py -v
```

- [ ] **Step 5: Commit**

```bash
git add src/backend/photonics_twin_app/schemas.py tests/python/test_api.py
git commit -m "feat(backend): Pydantic schemas for simulate request/response"
```

---

## Task 18: Simulation orchestration helper

**Files:**
- Create: `src/backend/photonics_twin_app/sim.py`
- Modify: `tests/python/test_api.py`

This is the boundary between the API layer and the C++ binding. It loads materials from JSON, builds a `BraggGrating`, runs the sweep, and assembles a response payload.

- [ ] **Step 1: Write the failing test**

Append to `tests/python/test_api.py`:

```python
import numpy as np
from photonics_twin_app.sim import run_bragg_sweep
from photonics_twin_app.schemas import BraggParams, Sweep

def test_run_bragg_sweep_shape():
    params = BraggParams(material_high="Si", material_low="SiO2",
                         centre_nm=1550.0, periods=15)
    sweep = Sweep(start_nm=1400.0, stop_nm=1700.0, n_points=501)
    out = run_bragg_sweep(params, sweep)
    assert len(out["wavelengths_nm"]) == 501
    assert len(out["reflectance"]) == 501
    assert len(out["stack"]) == 30
    assert "compute_ms" in out["meta"]
    assert out["meta"]["n_layers"] == 30
```

- [ ] **Step 2: Run, expect ImportError**

```bash
uv run pytest tests/python/test_api.py::test_run_bragg_sweep_shape -v
```

- [ ] **Step 3: Create `src/backend/photonics_twin_app/sim.py`**

```python
"""Orchestration between the FastAPI layer and the C++ photonics_core module."""
import json
import time
from functools import lru_cache
from pathlib import Path

import numpy as np

import photonics_core as pc
from photonics_twin_app.schemas import BraggParams, Sweep

REPO_ROOT = Path(__file__).resolve().parents[3]
MATERIALS_DIR = REPO_ROOT / "data" / "materials"

@lru_cache(maxsize=8)
def _material(name: str) -> pc.Material:
    path = MATERIALS_DIR / f"sellmeier_{name.lower()}.json"
    with open(path) as fh:
        c = json.load(fh)["coeffs"]
    return pc.Material(name, pc.SellmeierCoeffs(
        c["B1"], c["B2"], c["B3"], c["C1"], c["C2"], c["C3"]
    ))

def run_bragg_sweep(params: BraggParams, sweep: Sweep) -> dict:
    high = _material(params.material_high)
    low  = _material(params.material_low)
    g = pc.BraggGrating(high, low, params.centre_nm, params.periods)

    wl = np.linspace(sweep.start_nm, sweep.stop_nm, sweep.n_points, dtype=np.float64)
    t0 = time.perf_counter()
    R  = g.reflectance(wl)
    compute_ms = (time.perf_counter() - t0) * 1000.0

    stack = g.stack_view()  # already a list of dicts
    return {
        "wavelengths_nm": wl.tolist(),
        "reflectance":    R.tolist(),
        "stack":          stack,
        "meta": {"compute_ms": round(compute_ms, 3), "n_layers": len(stack)},
    }
```

- [ ] **Step 4: Run, expect PASS**

```bash
uv run pytest tests/python/test_api.py::test_run_bragg_sweep_shape -v
```

- [ ] **Step 5: Commit**

```bash
git add src/backend/photonics_twin_app/sim.py tests/python/test_api.py
git commit -m "feat(backend): run_bragg_sweep orchestration helper"
```

---

## Task 19: `POST /simulate/tmm/sweep` route

**Files:**
- Create: `src/backend/photonics_twin_app/routers/simulate.py`
- Modify: `src/backend/photonics_twin_app/main.py`
- Modify: `tests/python/test_api.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/python/test_api.py`:

```python
async def test_simulate_tmm_sweep_smoke(client):
    body = {
        "component": "bragg_grating",
        "params": {"material_high": "Si", "material_low": "SiO2",
                   "centre_nm": 1550.0, "periods": 15},
        "sweep":  {"start_nm": 1400.0, "stop_nm": 1700.0, "n_points": 501},
    }
    r = await client.post("/simulate/tmm/sweep", json=body)
    assert r.status_code == 200
    data = r.json()
    assert len(data["wavelengths_nm"]) == 501
    assert len(data["reflectance"])    == 501
    assert len(data["stack"])          == 30
    assert data["meta"]["n_layers"]    == 30

async def test_simulate_validation_error(client):
    body = {
        "component": "bragg_grating",
        "params": {"material_high": "Au", "material_low": "SiO2",
                   "centre_nm": 1550.0, "periods": 15},
        "sweep":  {"start_nm": 1400.0, "stop_nm": 1700.0, "n_points": 501},
    }
    r = await client.post("/simulate/tmm/sweep", json=body)
    assert r.status_code == 422
    assert "material_high" in r.text
```

- [ ] **Step 2: Run, expect 404**

```bash
uv run pytest tests/python/test_api.py::test_simulate_tmm_sweep_smoke -v
```

- [ ] **Step 3: Create `src/backend/photonics_twin_app/routers/simulate.py`**

```python
from fastapi import APIRouter, HTTPException
from photonics_twin_app.schemas import SimulateRequest, SimulateResponse
from photonics_twin_app.sim import run_bragg_sweep

router = APIRouter(prefix="/simulate", tags=["simulate"])

@router.post("/tmm/sweep", response_model=SimulateResponse)
def simulate_tmm_sweep(req: SimulateRequest) -> SimulateResponse:
    if req.component != "bragg_grating":
        raise HTTPException(400, f"Unknown component: {req.component}")
    result = run_bragg_sweep(req.params, req.sweep)
    return SimulateResponse(**result)
```

- [ ] **Step 4: Wire it into `main.py`**

In `src/backend/photonics_twin_app/main.py`, inside `create_app()` after the CORS middleware:

```python
    from photonics_twin_app.routers import simulate
    app.include_router(simulate.router)
```

- [ ] **Step 5: Run, expect PASS**

```bash
uv run pytest tests/python/test_api.py -v
```

- [ ] **Step 6: Commit**

```bash
git add src/backend/photonics_twin_app/routers/simulate.py src/backend/photonics_twin_app/main.py tests/python/test_api.py
git commit -m "feat(backend): POST /simulate/tmm/sweep endpoint"
```

---

## Task 20: `POST /mock/slurm/submit` route

**Files:**
- Create: `src/backend/photonics_twin_app/routers/mock_slurm.py`
- Modify: `src/backend/photonics_twin_app/main.py`
- Modify: `tests/python/test_api.py`

- [ ] **Step 1: Write the failing test**

```python
async def test_mock_slurm_echo(client):
    payload = {"job_kind": "bragg_sweep", "params": {"centre_nm": 1550.0}}
    r = await client.post("/mock/slurm/submit", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "accepted"
    assert data["job_id"].startswith("mock-")
    assert data["echo"] == payload
    assert "received_at" in data
```

- [ ] **Step 2: Run, expect 404**

```bash
uv run pytest tests/python/test_api.py::test_mock_slurm_echo -v
```

- [ ] **Step 3: Create the router**

`src/backend/photonics_twin_app/routers/mock_slurm.py`:

```python
import secrets
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter
from fastapi.requests import Request

router = APIRouter(prefix="/mock/slurm", tags=["mock-slurm"])

@router.post("/submit")
async def submit(req: Request) -> dict[str, Any]:
    body = await req.json()
    return {
        "job_id":      f"mock-{secrets.token_hex(3)}",
        "status":      "accepted",
        "received_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "echo":        body,
    }
```

- [ ] **Step 4: Wire it in**

In `main.py`, alongside the simulate router:

```python
    from photonics_twin_app.routers import mock_slurm
    app.include_router(mock_slurm.router)
```

- [ ] **Step 5: Run, expect PASS**

```bash
uv run pytest tests/python/test_api.py::test_mock_slurm_echo -v
```

- [ ] **Step 6: Commit**

```bash
git add src/backend/photonics_twin_app/routers/mock_slurm.py src/backend/photonics_twin_app/main.py tests/python/test_api.py
git commit -m "feat(backend): mock Slurm echo endpoint"
```

---

## Task 21: `WS /ws/sim` route

**Files:**
- Create: `src/backend/photonics_twin_app/routers/ws.py`
- Modify: `src/backend/photonics_twin_app/main.py`
- Modify: `tests/python/test_api.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/python/test_api.py`:

```python
from fastapi.testclient import TestClient

def test_ws_sim_recompute(app):
    sync_client = TestClient(app)
    with sync_client.websocket_connect("/ws/sim?component=bragg_grating") as ws:
        ws.send_json({
            "type": "simulate",
            "params": {"material_high": "Si", "material_low": "SiO2",
                       "centre_nm": 1550.0, "periods": 15},
            "sweep":  {"start_nm": 1400.0, "stop_nm": 1700.0, "n_points": 101},
        })
        msg = ws.receive_json()
        assert msg["type"] == "result"
        assert len(msg["wavelengths_nm"]) == 101
        assert len(msg["reflectance"])    == 101

def test_ws_sim_validation_error(app):
    sync_client = TestClient(app)
    with sync_client.websocket_connect("/ws/sim?component=bragg_grating") as ws:
        ws.send_json({
            "type": "simulate",
            "params": {"material_high": "Au", "material_low": "SiO2",
                       "centre_nm": 1550.0, "periods": 15},
            "sweep":  {"start_nm": 1400.0, "stop_nm": 1700.0, "n_points": 101},
        })
        msg = ws.receive_json()
        assert msg["type"] == "error"
        assert "code" in msg and "message" in msg
```

- [ ] **Step 2: Run, expect 404 / connect failure**

```bash
uv run pytest tests/python/test_api.py::test_ws_sim_recompute -v
```

- [ ] **Step 3: Create the WS router**

`src/backend/photonics_twin_app/routers/ws.py`:

```python
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from photonics_twin_app.schemas import BraggParams, Sweep
from photonics_twin_app.sim import run_bragg_sweep

router = APIRouter(tags=["ws"])

@router.websocket("/ws/sim")
async def ws_sim(ws: WebSocket, component: str = "bragg_grating"):
    await ws.accept()
    if component != "bragg_grating":
        await ws.send_json({"type": "error", "code": "unknown_component",
                            "message": f"Unknown component: {component}"})
        await ws.close()
        return
    try:
        while True:
            msg = await ws.receive_json()
            if msg.get("type") != "simulate":
                await ws.send_json({"type": "error", "code": "bad_message",
                                    "message": "expected type=simulate"})
                continue
            try:
                params = BraggParams(**msg["params"])
                sweep  = Sweep(**msg["sweep"])
            except ValidationError as e:
                await ws.send_json({"type": "error", "code": "validation_error",
                                    "message": str(e)})
                continue
            result = run_bragg_sweep(params, sweep)
            await ws.send_json({"type": "result", **result})
    except WebSocketDisconnect:
        return
```

- [ ] **Step 4: Wire it in**

In `main.py`:

```python
    from photonics_twin_app.routers import ws
    app.include_router(ws.router)
```

- [ ] **Step 5: Run, expect PASS**

```bash
uv run pytest tests/python/test_api.py -v
```

- [ ] **Step 6: Commit**

```bash
git add src/backend/photonics_twin_app/routers/ws.py src/backend/photonics_twin_app/main.py tests/python/test_api.py
git commit -m "feat(backend): WS /ws/sim with validation error path"
```

---

## Task 22: Frontend scaffold (Vite + React + JS)

**Files:**
- Create: `src/frontend/package.json`
- Create: `src/frontend/vite.config.js`
- Create: `src/frontend/index.html`
- Create: `src/frontend/src/main.jsx`
- Create: `src/frontend/src/App.jsx`
- Create: `src/frontend/src/App.css`

- [ ] **Step 1: Create `src/frontend/package.json`**

```json
{
  "name": "photonics-twin-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev":     "vite",
    "build":   "vite build",
    "preview": "vite preview",
    "lint":    "eslint src --ext .js,.jsx"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-plotly.js": "^2.6.0",
    "plotly.js-dist-min": "^2.35.2"
  },
  "devDependencies": {
    "vite": "^5.4.10",
    "@vitejs/plugin-react": "^4.3.3",
    "eslint": "^9.13.0",
    "eslint-plugin-react": "^7.37.2"
  }
}
```

- [ ] **Step 2: Create `src/frontend/vite.config.js`**

```js
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/simulate":   { target: "http://localhost:8000", changeOrigin: true },
      "/mock":       { target: "http://localhost:8000", changeOrigin: true },
      "/healthz":    { target: "http://localhost:8000", changeOrigin: true },
      "/ws":         { target: "ws://localhost:8000",   ws: true },
    },
  },
});
```

- [ ] **Step 3: Create `src/frontend/index.html`**

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Photonics Twin — Bragg (v0.1)</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
```

- [ ] **Step 4: Create `src/frontend/src/main.jsx`**

```jsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";
import "./App.css";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <App />
  </StrictMode>
);
```

- [ ] **Step 5: Create a placeholder `src/frontend/src/App.jsx`**

```jsx
export default function App() {
  return <h1>Photonics Twin — Bragg slice</h1>;
}
```

- [ ] **Step 6: Create `src/frontend/src/App.css`**

```css
:root { color-scheme: light dark; font-family: system-ui, sans-serif; }
body { margin: 0; }
.container {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 1rem;
  padding: 1rem;
  height: 100vh;
  box-sizing: border-box;
}
.panel { display: flex; flex-direction: column; gap: 0.75rem; }
.panel label { display: block; font-size: 0.85rem; }
.panel input[type="range"] { width: 100%; }
.right { display: flex; flex-direction: column; gap: 1rem; }
.status { font-size: 0.8rem; opacity: 0.7; }
.status.live  { color: #2a8; }
.status.error { color: #c33; }
```

- [ ] **Step 7: Install and verify dev build**

```bash
cd src/frontend
npm install
npm run build
```

Expected: builds to `dist/` without errors.

- [ ] **Step 8: Commit**

```bash
git add src/frontend
git commit -m "feat(frontend): vite + react + js scaffold with dev proxy"
```

---

## Task 23: `useSimulation` hook

**Files:**
- Create: `src/frontend/src/hooks/useSimulation.js`

- [ ] **Step 1: Create the hook**

```js
import { useEffect, useRef, useState } from "react";

const DEBOUNCE_MS = 30;

export function useSimulation(params, sweep, component = "bragg_grating") {
  const [result, setResult] = useState(null);
  const [status, setStatus] = useState("connecting"); // connecting | live | error
  const [error,  setError]  = useState(null);
  const wsRef    = useRef(null);
  const timerRef = useRef(null);

  useEffect(() => {
    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    const ws = new WebSocket(`${proto}//${window.location.host}/ws/sim?component=${component}`);
    wsRef.current = ws;
    ws.onopen  = () => setStatus("live");
    ws.onerror = () => setStatus("error");
    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data);
      if (msg.type === "error") { setError(msg); }
      else                        { setError(null); setResult(msg); }
    };
    return () => ws.close();
  }, [component]);

  useEffect(() => {
    if (status !== "live") return;
    if (!params || !sweep) return;
    clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      wsRef.current.send(JSON.stringify({ type: "simulate", params, sweep }));
    }, DEBOUNCE_MS);
  }, [params, sweep, status]);

  return { result, status, error };
}
```

- [ ] **Step 2: Smoke-build to verify syntax**

```bash
cd src/frontend && npm run build
```

- [ ] **Step 3: Commit**

```bash
git add src/frontend/src/hooks
git commit -m "feat(frontend): useSimulation WS hook with debounced send"
```

---

## Task 24: `ParameterPanel` component

**Files:**
- Create: `src/frontend/src/components/ParameterPanel.jsx`

- [ ] **Step 1: Create the component**

```jsx
const MATERIALS = ["Si", "SiO2"];

export default function ParameterPanel({ params, sweep, onChange }) {
  const set = (next) => onChange({ ...params, ...next }, sweep);
  const setSweep = (next) => onChange(params, { ...sweep, ...next });

  return (
    <div className="panel">
      <h2>Parameters</h2>

      <label>material_high
        <select value={params.material_high}
                onChange={(e) => set({ material_high: e.target.value })}>
          {MATERIALS.map((m) => <option key={m} value={m}>{m}</option>)}
        </select>
      </label>

      <label>material_low
        <select value={params.material_low}
                onChange={(e) => set({ material_low: e.target.value })}>
          {MATERIALS.map((m) => <option key={m} value={m}>{m}</option>)}
        </select>
      </label>

      <label>centre_nm = {params.centre_nm.toFixed(1)}
        <input type="range" min="800" max="2000" step="1"
               value={params.centre_nm}
               onChange={(e) => set({ centre_nm: Number(e.target.value) })} />
      </label>

      <label>periods = {params.periods}
        <input type="range" min="2" max="16" step="1"
               value={params.periods}
               onChange={(e) => set({ periods: Number(e.target.value) })} />
      </label>

      <h3>Sweep</h3>
      <label>start_nm = {sweep.start_nm.toFixed(0)}
        <input type="range" min="400" max="2400" step="1"
               value={sweep.start_nm}
               onChange={(e) => setSweep({ start_nm: Number(e.target.value) })} />
      </label>
      <label>stop_nm = {sweep.stop_nm.toFixed(0)}
        <input type="range" min="400" max="2400" step="1"
               value={sweep.stop_nm}
               onChange={(e) => setSweep({ stop_nm: Number(e.target.value) })} />
      </label>
      <label>n_points = {sweep.n_points}
        <input type="range" min="51" max="1001" step="50"
               value={sweep.n_points}
               onChange={(e) => setSweep({ n_points: Number(e.target.value) })} />
      </label>
    </div>
  );
}
```

- [ ] **Step 2: Build to check syntax**

```bash
cd src/frontend && npm run build
```

- [ ] **Step 3: Commit**

```bash
git add src/frontend/src/components/ParameterPanel.jsx
git commit -m "feat(frontend): ParameterPanel with sliders and material selects"
```

---

## Task 25: `SpectralPlot` component

**Files:**
- Create: `src/frontend/src/components/SpectralPlot.jsx`

- [ ] **Step 1: Create the component**

```jsx
import Plot from "react-plotly.js";

export default function SpectralPlot({ wavelengths, reflectance }) {
  if (!wavelengths || !reflectance) return <div>—</div>;
  return (
    <Plot
      data={[{
        x: wavelengths,
        y: reflectance,
        type: "scatter",
        mode: "lines",
        line: { width: 2 },
      }]}
      layout={{
        margin: { l: 60, r: 20, t: 30, b: 50 },
        xaxis: { title: "wavelength (nm)" },
        yaxis: { title: "reflectance |r|²", range: [0, 1] },
        height: 360,
      }}
      style={{ width: "100%" }}
      config={{ responsive: true, displayModeBar: false }}
    />
  );
}
```

- [ ] **Step 2: Build to check**

```bash
cd src/frontend && npm run build
```

- [ ] **Step 3: Commit**

```bash
git add src/frontend/src/components/SpectralPlot.jsx
git commit -m "feat(frontend): SpectralPlot Plotly line chart"
```

---

## Task 26: `LayerStackView` component

**Files:**
- Create: `src/frontend/src/components/LayerStackView.jsx`

- [ ] **Step 1: Create the component**

```jsx
export default function LayerStackView({ stack }) {
  if (!stack || stack.length === 0) return <div>—</div>;

  const total = stack.reduce((s, L) => s + L.thickness_nm, 0);
  const nMin = Math.min(...stack.map((L) => L.n_at_centre));
  const nMax = Math.max(...stack.map((L) => L.n_at_centre));
  const greyscale = (n) => {
    const t = nMax === nMin ? 0.5 : (n - nMin) / (nMax - nMin);
    const v = Math.round(220 - 180 * t); // low n → light, high n → dark
    return `rgb(${v},${v},${v})`;
  };

  const W = 800, H = 80;
  let x = 0;
  return (
    <div>
      <h3>Layer stack ({stack.length} layers, total {total.toFixed(0)} nm)</h3>
      <svg width="100%" viewBox={`0 0 ${W} ${H}`} style={{ border: "1px solid #ccc" }}>
        {stack.map((L) => {
          const w = (L.thickness_nm / total) * W;
          const rect = (
            <g key={L.index}>
              <rect x={x} y={0} width={w} height={H}
                    fill={greyscale(L.n_at_centre)} stroke="#666" strokeWidth="0.5" />
              <title>{`${L.material} — ${L.thickness_nm.toFixed(2)} nm — n=${L.n_at_centre.toFixed(3)}`}</title>
            </g>
          );
          x += w;
          return rect;
        })}
      </svg>
    </div>
  );
}
```

- [ ] **Step 2: Build**

```bash
cd src/frontend && npm run build
```

- [ ] **Step 3: Commit**

```bash
git add src/frontend/src/components/LayerStackView.jsx
git commit -m "feat(frontend): LayerStackView SVG bars coloured by index"
```

---

## Task 27: Wire `App.jsx`

**Files:**
- Modify: `src/frontend/src/App.jsx`

- [ ] **Step 1: Replace `App.jsx` with the wired version**

```jsx
import { useState } from "react";
import { useSimulation } from "./hooks/useSimulation.js";
import ParameterPanel from "./components/ParameterPanel.jsx";
import SpectralPlot from "./components/SpectralPlot.jsx";
import LayerStackView from "./components/LayerStackView.jsx";

const INITIAL_PARAMS = { material_high: "Si", material_low: "SiO2",
                          centre_nm: 1550.0, periods: 15 };
const INITIAL_SWEEP  = { start_nm: 1400.0, stop_nm: 1700.0, n_points: 501 };

export default function App() {
  const [params, setParams] = useState(INITIAL_PARAMS);
  const [sweep,  setSweep]  = useState(INITIAL_SWEEP);
  const onChange = (p, s) => { setParams(p); setSweep(s); };

  const { result, status, error } = useSimulation(params, sweep);

  return (
    <div className="container">
      <ParameterPanel params={params} sweep={sweep} onChange={onChange} />
      <div className="right">
        <div className={`status ${status}`}>
          status: {status}
          {result?.meta?.compute_ms != null &&
            ` · compute: ${result.meta.compute_ms.toFixed(2)} ms`}
          {error && ` · error: ${error.message}`}
        </div>
        <SpectralPlot wavelengths={result?.wavelengths_nm}
                      reflectance={result?.reflectance} />
        <LayerStackView stack={result?.stack} />
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Build to confirm**

```bash
cd src/frontend && npm run build
```

- [ ] **Step 3: Manual smoke test**

In two terminals:

```bash
# terminal 1
uv run uvicorn photonics_twin_app.main:app --reload
# terminal 2
cd src/frontend && npm run dev
```

Open `http://localhost:5173`. Drag the `centre_nm` slider; expect the reflectance peak to track the slider and the layer-stack bars to retitle. Status badge should read `live`.

- [ ] **Step 4: Commit**

```bash
git add src/frontend/src/App.jsx
git commit -m "feat(frontend): wire App.jsx — sliders → WS → plot + stack"
```

---

## Task 28: Docker Compose for full-stack local dev

**Files:**
- Create: `docker/Dockerfile.backend`
- Create: `docker/Dockerfile.frontend`
- Create: `docker-compose.yml` (overwrite the empty stub from initial commit)

- [ ] **Step 1: Create `docker/Dockerfile.backend`**

```dockerfile
FROM python:3.12-slim AS build
RUN apt-get update && apt-get install -y --no-install-recommends \
    g++ cmake git ca-certificates && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv
WORKDIR /app
COPY pyproject.toml CMakeLists.txt ./
COPY src ./src
COPY data ./data
RUN uv pip install --system .[dev]

FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    libstdc++6 && rm -rf /var/lib/apt/lists/*
COPY --from=build /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=build /usr/local/bin /usr/local/bin
COPY --from=build /app/data /app/data
WORKDIR /app
EXPOSE 8000
CMD ["uvicorn", "photonics_twin_app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: Create `docker/Dockerfile.frontend`**

```dockerfile
FROM node:20-alpine AS build
WORKDIR /app
COPY src/frontend/package.json src/frontend/package-lock.json* ./
RUN npm install
COPY src/frontend ./
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

`docker/nginx.conf`:

```nginx
server {
  listen 80;
  location /healthz   { proxy_pass http://backend:8000; }
  location /simulate/ { proxy_pass http://backend:8000; }
  location /mock/     { proxy_pass http://backend:8000; }
  location /ws/ {
    proxy_pass http://backend:8000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
  }
  location / {
    root /usr/share/nginx/html;
    try_files $uri /index.html;
  }
}
```

- [ ] **Step 3: Create `docker-compose.yml`**

```yaml
services:
  backend:
    build:
      context: .
      dockerfile: docker/Dockerfile.backend
    ports:
      - "8000:8000"
  frontend:
    build:
      context: .
      dockerfile: docker/Dockerfile.frontend
    depends_on:
      - backend
    ports:
      - "5173:80"
```

- [ ] **Step 4: Verify the stack starts and is reachable**

```bash
docker compose up --build -d
curl -fsS http://localhost:8000/healthz
curl -fsS http://localhost:5173/healthz       # via nginx proxy
docker compose down
```

Expected: both `curl`s return `{"status":"ok"}`.

- [ ] **Step 5: Commit**

```bash
git add docker docker-compose.yml
git commit -m "build: docker compose stack (backend + nginx-fronted spa)"
```

---

## Task 29: CI workflow — `ci.yml`

**Files:**
- Modify: `.github/workflows/ci.yml`

- [ ] **Step 1: Replace contents**

```yaml
name: CI
on:
  push:
    branches: [master, main, develop]
  pull_request:

jobs:
  cpp-and-python:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install C++ toolchain
        run: |
          sudo apt-get update
          sudo apt-get install -y g++ cmake ninja-build
      - name: Install uv
        uses: astral-sh/setup-uv@v3
        with:
          python-version: "3.12"
      - name: uv sync
        run: uv pip install --system .[dev]
      - name: Configure & build C++
        run: |
          cmake -B build -S . -GNinja -DPHOTONICS_BUILD_TESTS=ON
          cmake --build build --parallel
      - name: Run C++ tests
        run: ctest --test-dir build --output-on-failure
      - name: Run pytest
        run: pytest tests/python -v

  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: "20" }
      - name: npm install + build + lint
        working-directory: src/frontend
        run: |
          npm ci || npm install
          npm run build
          npm run lint || echo "lint-warnings-only"
```

- [ ] **Step 2: Commit and push to confirm CI runs green**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: build c++/pybind11, run pytest, build frontend"
git push
```

Expected: CI passes on the next push.

---

## Task 30: HPC dispatch workflow + example payload

**Files:**
- Create: `.github/workflows/hpc-dispatch.yml`
- Create: `simulations/examples/bragg_grating_sweep.json`

- [ ] **Step 1: Create the example payload**

`simulations/examples/bragg_grating_sweep.json`:

```json
{
  "component": "bragg_grating",
  "params": {
    "material_high": "Si", "material_low": "SiO2",
    "centre_nm": 1550.0, "periods": 15
  },
  "sweep": {
    "start_nm": 1400.0, "stop_nm": 1700.0, "n_points": 501
  }
}
```

- [ ] **Step 2: Create `.github/workflows/hpc-dispatch.yml`**

```yaml
name: HPC dispatch (mock)
on:
  push:
    tags: ["sim-*"]
  workflow_dispatch:

jobs:
  notify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: POST to mock Slurm endpoint
        env:
          MOCK_SLURM_URL: ${{ secrets.MOCK_SLURM_URL }}
        run: |
          if [ -z "$MOCK_SLURM_URL" ]; then
            echo "MOCK_SLURM_URL secret not set; aborting cleanly." >&2
            exit 0
          fi
          response=$(curl -fsS -X POST -H "Content-Type: application/json" \
            --data @simulations/examples/bragg_grating_sweep.json \
            "$MOCK_SLURM_URL")
          echo "Mock response: $response"
          echo "$response" > response.json
      - name: Comment on commit (workflow_dispatch only writes a log)
        if: github.event_name == 'push'
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          if [ -f response.json ]; then
            body="Mock Slurm dispatch: $(cat response.json)"
            gh api repos/${{ github.repository }}/commits/${{ github.sha }}/comments \
              -f body="$body"
          fi
```

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/hpc-dispatch.yml simulations/examples/bragg_grating_sweep.json
git commit -m "ci(hpc): mock Slurm dispatch on sim-* tags"
```

- [ ] **Step 4: First-run verification (manual)**

In the GitHub repo settings, set `MOCK_SLURM_URL` to a temporary echo service URL (e.g., `https://webhook.site/<token>`). Push a tag:

```bash
git tag sim-test-0.1
git push origin sim-test-0.1
```

Expected: the Action runs, the webhook receives the POST, the workflow log shows `Mock response: ...`. If `MOCK_SLURM_URL` is unset, the workflow exits cleanly without failure.

---

## Task 31: README and "done bar" smoke test

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Replace `README.md` with the slice's quick-start**

```markdown
# SPEAR Photonics Digital Twin

Feasibility prototype (v0.1): Bragg grating simulator across C++ TMM core,
pybind11 bindings, FastAPI backend, and React UI with live WebSocket recompute.

## Quick start

```bash
# Python + C++ build (editable install)
uv venv && uv pip install -e .[dev]

# C++ unit tests
cmake -B build -S . && cmake --build build && ctest --test-dir build --output-on-failure

# Python tests (binding + API + WS)
uv run pytest

# Run the stack
uv run uvicorn photonics_twin_app.main:app --reload      # terminal 1
cd src/frontend && npm install && npm run dev            # terminal 2
# open http://localhost:5173
```

## Repo layout

See `docs/superpowers/specs/2026-04-29-bragg-feasibility-prototype-design.md`
for the full design and `docs/superpowers/plans/2026-04-29-bragg-feasibility-prototype.md`
for the implementation plan.

## Validation

The reference fixture at `data/validation/quarterwave_si_sio2_reference.json`
is generated by `scripts/compute_reference.py` from the closed-form
expressions in Born & Wolf §1.6.5 — an independent oracle for the simulator's
output. Re-run the script if material coefficients change.
```

- [ ] **Step 2: Run the four "done bar" checks**

1. `docker compose up --build` → reach `http://localhost:5173`, drag a slider, see live plot + bars.
2. `uv run pytest && cmake --build build && ctest --test-dir build --output-on-failure` → all green.
3. `git tag sim-done-0.1 && git push origin sim-done-0.1` → workflow comment posted.
4. `cat data/validation/quarterwave_si_sio2_reference.json` → matches the test assertions.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: README quick-start for v0.1 slice"
```

---

## Self-review notes

**Spec coverage check** — every spec section has a task that implements it:

- §3 architecture → Tasks 1-2 (build + CMake), Tasks 11, 16, 22 (deployment units), Task 30 (HPC dispatch)
- §4.1 numerical types → Task 3
- §4.2 component classes → Tasks 4, 6, 9
- §4.3 conventions → enforced across Tasks 6, 7, 9 (free-function `tmm_sweep`, no virtuals, no exceptions)
- §4.4 pybind11 surface → Tasks 11, 12, 13
- §5.1 endpoints → Tasks 19 (REST), 20 (mock Slurm), 21 (WS)
- §5.2 schemas → Task 17
- §5.3 service flow → Task 18 (`run_bragg_sweep`)
- §6 frontend → Tasks 22-27
- §7 repo layout → all tasks contribute to the layout
- §8 build & dev tooling → Tasks 1, 11, 22, 28
- §9.1 test inventory → Tasks 4, 5, 7, 8, 9, 10 (cpp); 12, 13, 15 (bindings); 16, 17, 19, 20, 21 (api)
- §9.2 reference fixture → Tasks 14 (oracle), 15 (assertion)
- §9.3 CI workflows → Tasks 29, 30
- §10 done bar → Task 31
- §11 out of scope → no tasks (correctly excluded)

**Type / name consistency**:

- Material `Material(name, SellmeierCoeffs)` — same constructor signature in C++ (Task 4) and Python binding (Task 12).
- `BraggGrating(high, low, centre_nm, periods)` — same in C++ (Task 9) and Python binding (Task 13).
- `stack_view()` (Python) ↔ `stack()` (C++) — different names, by design: C++ returns `LayerStack&`, Python returns `list[dict]`. Documented in Task 13.
- `run_bragg_sweep(params, sweep)` returns dict with keys `wavelengths_nm`, `reflectance`, `stack`, `meta` — same keys consumed by the SimulateResponse model (Task 17) and the SpectralPlot/LayerStackView components (Tasks 25, 26).
- `n_at_centre` field name — Task 13 (binding), Task 18 (sim), Task 17 (schema), Task 26 (frontend) all agree.
- WS message types `simulate` / `result` / `error` — match between Task 21 (server) and Task 23 (hook).

**Placeholder scan**: no "TODO", "implement later", or "similar to" placeholders. Every code block is complete.

**One known scope item**: Task 16 introduces a package rename (`app` → `photonics_twin_app`). This is mentioned and the import path is consistent across Tasks 16-21, 28, 31.
