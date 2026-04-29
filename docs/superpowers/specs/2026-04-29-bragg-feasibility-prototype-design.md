# Bragg Grating Feasibility Prototype — Design Spec

**SPEAR Photonics Digital Twin | v0.1 | 2026-04-29**

---

## 1. Purpose & scope

This spec defines the first vertical slice of the Photonics Digital Twin platform: an end-to-end Bragg grating simulator covering the C++ physics core, Python bindings, FastAPI backend, React frontend, and a mocked GitHub-Actions-to-Slurm dispatch path. The slice exists to retire integration risk across every layer of the eventual stack while keeping the physics deliberately minimal (uniform, lossless Si/SiO₂ stack with Sellmeier dispersion).

This is sub-project #1 of the broader programme described in `docs/photonics_twin_technical_design_notes.md`. Subsequent sub-projects (HLS port, additional components, ML surrogates, real Slurm integration) are out of scope here and will each be designed in their own spec.

The "done" bar is described in §10.

## 2. Stack

| Layer | Technology | Notes |
|---|---|---|
| Physics core | C++17 | HLS-friendly conventions baked in from day one (§4) |
| Python bridge | pybind11 | Thin layer, no business logic |
| Backend | FastAPI (Python 3.12) | Sync REST + WebSocket, no Celery/Redis in this slice |
| Frontend | React + JavaScript (no TypeScript) + Vite + Plotly | One page, three components |
| Build | scikit-build-core + CMake (C++/pybind11), uv (Python), npm + Vite (frontend) | Docker Compose for full-stack local dev |
| HPC dispatch | GitHub Actions → mocked HTTP endpoint inside the backend | Real Slurm is a later sub-project |
| Tests | GoogleTest, pytest, no frontend tests in v0.1 | One literature-validated reference fixture |

The C++ choice is the original design-doc rationale: a single source compiles for both CPU simulation and FPGA via Vitis HLS, eliminating algorithm re-implementation when transitioning to hardware.

## 3. Architecture

```
                                ┌──────────────────────────────────┐
                                │   GitHub Actions (parallel)      │
                                │   tag: sim-* → mock-slurm POST   │
                                └─────────────────┬────────────────┘
                                                  │
                                                  ▼
┌────────────────┐   WebSocket   ┌──────────────────────────────────┐
│ React + JS UI  │◄─────────────►│   FastAPI backend                │
│ (Vite, Plotly) │   /ws/sim     │   src/backend/app                │
│  - sliders     │               │  ┌──────────────────────────┐    │
│  - reflectance │               │  │ /simulate/tmm/sweep      │    │
│  - layer stack │   REST POST   │  │ /mock/slurm/submit       │    │
└────────────────┘──────────────►│  │ /ws/sim                  │    │
                                 │  └────────────┬─────────────┘    │
                                 │               │ pybind11         │
                                 │               ▼                  │
                                 │  ┌──────────────────────────┐    │
                                 │  │ photonics_core (C++)     │    │
                                 │  │  Material, LayerStack,   │    │
                                 │  │  BraggGrating, tmm_sweep │    │
                                 │  └──────────────────────────┘    │
                                 └──────────────────────────────────┘
```

Three deployment units:

1. `photonics_core` — C++17 static lib + pybind11 module, installed into the Python env.
2. `backend` — FastAPI app importing `photonics_core`, exposing three endpoints.
3. `frontend` — React + JS Vite app, one page.

Plus one parallel-track artefact:

4. `.github/workflows/hpc-dispatch.yml` — fires on `sim-*` tag, POSTs a fixed payload to `/mock/slurm/submit`, posts a workflow comment with the response.

## 4. C++ core

### 4.1 Numerical types — the dual-build trick

Every kernel uses `photonics::real_t` and `photonics::complex_t`. CPU build defines no macro (so `real_t = double`); HLS build defines `PHOTONICS_HLS_BUILD` and pulls in `ap_fixed`.

```cpp
// include/photonics/common.hpp
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
}
```

### 4.2 Component classes

```cpp
// materials.hpp
struct SellmeierCoeffs { real_t B1, B2, B3, C1, C2, C3; };
class Material {
  SellmeierCoeffs c_;
  std::string name_;
public:
  Material(std::string name, SellmeierCoeffs c);
  real_t   n(real_t wavelength_nm) const;
  const std::string& name() const;
};

// tmm.hpp
struct Layer { real_t thickness_nm; const Material* material; };
class LayerStack {
  std::vector<Layer> layers_;        // CPU only; HLS swaps to fixed array
public:
  void add_layer(real_t thickness_nm, const Material& m);
  std::size_t size() const;
  const Layer& at(std::size_t i) const;
};

// Free function — the HLS synthesis target.
void tmm_sweep(const LayerStack& stack,
               const real_t* wavelengths_nm, std::size_t n_wl,
               complex_t* r_out, complex_t* t_out);

// bragg.hpp
class BraggGrating {
  Material high_, low_;
  real_t centre_nm_;
  std::size_t periods_;
  LayerStack cached_stack_;
public:
  BraggGrating(Material high, Material low, real_t centre_nm, std::size_t periods);
  void set_centre_nm(real_t v);
  void set_periods(std::size_t v);
  const LayerStack& stack() const;
  void reflectance(const real_t* wl, std::size_t n_wl, real_t* R_out) const;  // |r|^2
};
```

### 4.3 Conventions (priority order)

1. `tmm_sweep` is a free function with C-style array I/O; classes are fine for orchestration but the inner loop crosses no class boundaries. This is the HLS synthesis target.
2. No `std::vector` inside the synthesis target. Stack is unwrapped to raw arrays at the boundary.
3. No virtuals, no exceptions inside core. Errors are status codes returned from the binding layer.
4. `MAX_LAYERS = 32` is a hard cap, matching the HLS BRAM budget. Enforced at the Pydantic boundary (§5.2). The C++ classes treat it as a documented precondition (asserted in debug builds) rather than a runtime check, so the CPU and HLS builds carry identical algorithmic code.
5. `BraggGrating::reflectance()` returns `|r|²` directly. A `complex_amplitudes()` accessor is added only when something asks for it.
6. Material lifetime: `LayerStack` stores `const Material*` — callers must ensure the referenced `Material` outlives the stack. `BraggGrating` satisfies this by holding `Material` members directly and pointing its `cached_stack_` at them.

### 4.4 pybind11 surface

Thin bindings, NumPy in/out via the buffer protocol, zero-copy where possible.

```cpp
PYBIND11_MODULE(photonics_core, m) {
  py::class_<Material>(m, "Material")
      .def(py::init<std::string, SellmeierCoeffs>())
      .def("n", &Material::n)
      .def_property_readonly("name", &Material::name);

  py::class_<LayerStack>(m, "LayerStack")
      .def(py::init<>())
      .def("add_layer", &LayerStack::add_layer)
      .def("__len__", &LayerStack::size);

  py::class_<BraggGrating>(m, "BraggGrating")
      .def(py::init<Material, Material, double, std::size_t>())
      .def("set_centre_nm", &BraggGrating::set_centre_nm)
      .def("set_periods",   &BraggGrating::set_periods)
      .def("reflectance", [](const BraggGrating& self, py::array_t<double> wl){
          auto buf = wl.request();
          py::array_t<double> R(buf.size);
          self.reflectance(static_cast<double*>(buf.ptr), buf.size,
                           static_cast<double*>(R.request().ptr));
          return R;
      });
}
```

## 5. Backend API

### 5.1 Endpoints

**`POST /simulate/tmm/sweep`** — synchronous. Request:

```jsonc
{
  "component": "bragg_grating",
  "params": {
    "material_high": "Si",
    "material_low":  "SiO2",
    "centre_nm":     1550.0,
    "periods":       15
  },
  "sweep": { "start_nm": 1400.0, "stop_nm": 1700.0, "n_points": 501 }
}
```

Response:

```jsonc
{
  "wavelengths_nm": [/* 501 floats */],
  "reflectance":    [/* 501 floats */],
  "stack": [
    { "index": 0, "material": "Si",   "thickness_nm": 110.7, "n_at_centre": 3.476 },
    { "index": 1, "material": "SiO2", "thickness_nm": 267.2, "n_at_centre": 1.450 }
    /* ... */
  ],
  "meta": { "compute_ms": 0.42, "n_layers": 30 }
}
```

**`WS /ws/sim?component=bragg_grating`** — full-duplex.

- Client sends `{ "type": "simulate", "params": ..., "sweep": ... }`.
- Server replies with messages of type `result` (same body as REST minus `component`) or `error` (`{ "type":"error", "code":"...", "message":"..." }`).
- Stateless per message. No session, no in-flight cancellation in this slice.
- Client is responsible for debouncing (30 ms recommended, see §6.3).

**`POST /mock/slurm/submit`** — echo-mode mock for the GitHub Action.

```jsonc
// response:
{
  "job_id":      "mock-7f3a91",
  "status":      "accepted",
  "received_at": "2026-04-29T11:42:03Z",
  "echo":        { /* request body verbatim */ }
}
```

### 5.2 Pydantic schemas

```python
# src/backend/app/schemas.py
from pydantic import BaseModel, Field, conint, confloat

class BraggParams(BaseModel):
    material_high: str = Field(pattern="^(Si|SiO2)$")
    material_low:  str = Field(pattern="^(Si|SiO2)$")
    centre_nm:     confloat(ge=400.0,  le=2500.0)
    periods:       conint(ge=2, le=16)        # 2*16 == MAX_LAYERS

class Sweep(BaseModel):
    start_nm:  confloat(ge=200.0,  le=3000.0)
    stop_nm:   confloat(ge=200.0,  le=3000.0)
    n_points:  conint(ge=11, le=4001)

class SimulateRequest(BaseModel):
    component: str
    params: BraggParams
    sweep:  Sweep

class LayerOut(BaseModel):
    index: int
    material: str
    thickness_nm: float
    n_at_centre:  float

class SimulateResponse(BaseModel):
    wavelengths_nm: list[float]
    reflectance:    list[float]
    stack: list[LayerOut]
    meta:  dict
```

Validation lives at the Pydantic layer. The C++ core trusts its inputs.

### 5.3 Service-layer flow per request

```
FastAPI route
  └─ validate via Pydantic                             (~µs)
  └─ resolve material names → photonics_core.Material
  └─ construct photonics_core.BraggGrating(...)
  └─ build numpy wavelengths array
  └─ call grating.reflectance(wavelengths)             (~ms; the only hot work)
  └─ derive `stack` payload from grating.stack()
  └─ assemble SimulateResponse, return
```

## 6. Frontend

### 6.1 Layout

One page, one container component (`App.jsx`), three children: parameter panel (sliders + dropdowns), spectral plot (Plotly line), layer stack view (SVG). No router, no global store, local component state via `useState` plus one custom hook for the WS connection.

### 6.2 Component responsibilities

| Component | Owns | Receives | Emits |
|---|---|---|---|
| `App.jsx` | params + sweep state, connection status | — | passes state down |
| `ParameterPanel.jsx` | nothing (controlled inputs) | `params, sweep, onChange` | `onChange(nextParams, nextSweep)` |
| `SpectralPlot.jsx` | nothing | `wavelengths, reflectance` | — |
| `LayerStackView.jsx` | nothing | `stack` array | — |
| `useSimulation` hook | WS socket, latest result, `compute_ms` | `params, sweep` (debounced) | `{ result, status, error }` |

### 6.3 The WS hook

```js
// src/hooks/useSimulation.js
import { useEffect, useRef, useState } from "react";

const DEBOUNCE_MS = 30;

export function useSimulation(params, sweep, component = "bragg_grating") {
  const [result, setResult] = useState(null);
  const [status, setStatus] = useState("connecting"); // connecting | live | error
  const [error,  setError]  = useState(null);
  const wsRef    = useRef(null);
  const timerRef = useRef(null);

  useEffect(() => {
    // Same-origin URL — Vite dev proxy (§6.5) forwards /ws/* to the backend in
    // development; in production the same path is fronted by nginx/Caddy.
    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    const ws = new WebSocket(`${proto}//${window.location.host}/ws/sim?component=${component}`);
    wsRef.current = ws;
    ws.onopen    = () => setStatus("live");
    ws.onerror   = () => setStatus("error");
    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data);
      if (msg.type === "error") setError(msg);
      else                       setResult(msg);
    };
    return () => ws.close();
  }, [component]);

  useEffect(() => {
    if (status !== "live") return;
    clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      wsRef.current.send(JSON.stringify({ type: "simulate", params, sweep }));
    }, DEBOUNCE_MS);
  }, [params, sweep, status]);

  return { result, status, error };
}
```

Two `useEffect`s with distinct dependency arrays: one owns the socket lifetime keyed on `component`, one owns the debounced send keyed on `params/sweep`. No reconnect logic in v0.1 — if the socket drops, the badge turns red and the user reloads.

### 6.4 LayerStackView

Plain SVG, one `<rect>` per layer. Width proportional to `thickness_nm`, fill colour interpolated by `n_at_centre` on a greyscale ramp (low n = light, high n = dark). About 30 lines total. Plotly is not involved in this view.

### 6.5 Tooling

- `npm create vite@latest frontend -- --template react` (the JS template).
- Dependencies: `react`, `react-dom`, `plotly.js-dist-min` (not full Plotly — saves ~4 MB), `react-plotly.js`.
- No state-management library, no UI kit, no Tailwind. Plain CSS in `App.css`.
- Vite dev proxy in `vite.config.js`: `'/ws' → ws://localhost:8000`, `'/api' → http://localhost:8000`. Avoids CORS in development.

## 7. Repository layout for this slice

```
src/
  core/
    CMakeLists.txt
    include/photonics/
      common.hpp
      materials.hpp
      tmm.hpp
      bragg.hpp
    src/
      materials.cpp
      tmm.cpp
      bragg.cpp
  bindings/
    CMakeLists.txt
    photonics_core.cpp
  backend/
    app/
      __init__.py
      main.py
      schemas.py
      routers/
        __init__.py
        simulate.py
        mock_slurm.py
        ws.py
  frontend/
    package.json
    vite.config.js
    src/
      App.jsx
      App.css
      main.jsx
      api.js
      hooks/
        useSimulation.js
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
tests/
  cpp/
    test_materials.cpp
    test_tmm.cpp
    test_bragg.cpp
  python/
    test_bindings.py
    test_api.py
docker/
  Dockerfile.backend
  Dockerfile.frontend
  Dockerfile.dev
docker-compose.yml
.github/workflows/
  ci.yml
  hpc-dispatch.yml
CMakeLists.txt
pyproject.toml
```

Items from the broader design doc explicitly excluded from this slice: `src/hdl/`, `src/models/`, `src/backend/app/services/`, `src/backend/app/workers/`, `notebooks/` beyond ad-hoc.

## 8. Build & dev tooling

- **C++ / pybind11:** scikit-build-core driven from `pyproject.toml`. Top-level `CMakeLists.txt` aggregates `src/core` and `src/bindings`. `cmake --build build --target test` runs GoogleTest.
- **Python:** uv. `uv sync` installs the editable `photonics-twin` package (which builds the C++ extension via scikit-build-core), FastAPI, and pytest. `.python-version` already pins 3.12.
- **Frontend:** npm + Vite. `cd src/frontend && npm ci && npm run dev`.
- **Full-stack local dev:** `docker-compose up` brings up backend (uvicorn on 8000) and frontend (vite on 5173). The mock-slurm endpoint lives inside the backend container — no separate service in this slice.

A Conda recipe for HPC deployment is out of scope here.

## 9. Testing & validation

### 9.1 Test inventory

| Test | Asserts |
|---|---|
| `test_materials.cpp::SellmeierSi_at_1550` | Si refractive index at 1550 nm matches table value within 1e-4 |
| `test_materials.cpp::SellmeierSiO2_at_633` | SiO₂ at 633 nm (HeNe) matches table value within 1e-4 |
| `test_tmm.cpp::SingleLayerNormalIncidence` | Hand-computed Fresnel reflectance, single Si layer on SiO₂ substrate |
| `test_tmm.cpp::FourLayerStack` | Hand-computed `\|r\|²` for a 4-layer stack |
| `test_bragg.cpp::StackHasCorrectLayerCount` | `BraggGrating(periods=15)` produces 30 layers |
| `test_bragg.cpp::QuarterWaveThicknessesAtCentre` | layer thicknesses = λ₀ / (4·n) within 1e-6 nm |
| `test_bindings.py::numpy_roundtrip` | passing 501 wavelengths returns 501 reflectances, dtype float64, contiguous |
| `test_bindings.py::reference_fixture` | reference JSON peak/edges within tolerance |
| `test_api.py::simulate_tmm_sweep_smoke` | POST /simulate/tmm/sweep returns 200 + 501 points |
| `test_api.py::simulate_validation_errors` | bad params return 422 with field-level error |
| `test_api.py::ws_sim_recompute` | open WS, send simulate, receive result message |
| `test_api.py::mock_slurm_echo` | POST /mock/slurm/submit echoes payload, returns mock job id |

No frontend tests in v0.1. UI is verified manually and indirectly via API integration tests.

### 9.2 The literature-validated reference fixture

Lives at `data/validation/quarterwave_si_sio2_reference.json`. Reference values are computed **analytically from the closed-form expressions in Born & Wolf §1.6.5** (a separate, independent implementation from the TMM under test) for a quarter-wave Si/SiO₂ stack centred on 1550 nm with 15 periods. Workflow:

1. Implementation plan includes a one-off Python script (`scripts/compute_reference.py`) that evaluates the Born & Wolf formulas for `peak_reflectance`, `stop_band_edge_low_nm`, and `stop_band_edge_high_nm` at the chosen material indices and stack geometry.
2. Its output is written into the JSON file once and committed.
3. The test harness then asserts the simulator's output matches those frozen reference values within tolerance — it does **not** call the script at test time.

This separation matters: if the TMM under test were used to seed its own reference, the test would only catch regressions, not initial correctness. Born & Wolf is the independent oracle.

```jsonc
{
  "description": "Si/SiO2 quarter-wave Bragg @ 1550 nm, 15 periods. Reference: Born & Wolf §1.6.5",
  "params": { "material_high": "Si", "material_low": "SiO2",
              "centre_nm": 1550.0, "periods": 15 },
  "sweep":  { "start_nm": 1400.0,  "stop_nm": 1700.0, "n_points": 501 },
  "reference": {
    "peak_reflectance":           "<filled by scripts/compute_reference.py>",
    "peak_reflectance_tol":       1e-3,
    "peak_wavelength_nm":         1550.0,
    "peak_wavelength_tol_nm":     0.5,
    "stop_band_edge_low_nm":      "<filled by scripts/compute_reference.py>",
    "stop_band_edge_high_nm":     "<filled by scripts/compute_reference.py>",
    "stop_band_edge_tol_nm":      2.0
  }
}
```

This file is the seed of the validation methodology: every future component drops its own `<component>_reference.json` next to it and the same test harness picks it up.

### 9.3 CI workflows

`.github/workflows/ci.yml` — runs on push and PR, two parallel jobs on `ubuntu-latest`:

```yaml
jobs:
  cpp-and-python:
    - checkout
    - install uv, python 3.12
    - install C++ toolchain (gcc-12, cmake, pybind11 via apt)
    - uv sync
    - cmake -B build -S . && cmake --build build --target test
    - uv run pytest tests/python -v
  frontend:
    - checkout
    - setup node 20
    - cd src/frontend && npm ci && npm run build && npm run lint
```

`.github/workflows/hpc-dispatch.yml` — runs on `sim-*` tags or manual dispatch:

```yaml
on:
  push: { tags: ['sim-*'] }
  workflow_dispatch:
jobs:
  notify:
    - checkout
    - curl -X POST $MOCK_SLURM_URL --data @simulations/examples/<file>.json
    - gh comment with response
```

`MOCK_SLURM_URL` is a repo secret. For first-run sanity it can point at an external echo service (e.g. webhook.site); once the backend is deployed somewhere reachable it points there.

Single Ubuntu runner is the deliberate choice for v0.1. Windows/macOS matrix is a fast-follow if cross-platform development becomes a hard requirement.

## 10. The "done" bar

A reviewer should be able to:

1. Clone the repo, run `docker-compose up`, and reach `http://localhost:5173` to drag a slider and see a live spectral plot + layer bars.
2. Run `uv run pytest && cmake --build build --target test` and see all green.
3. Push a tag `sim-test` and watch the GitHub Action post a workflow comment with `{"status":"accepted","job_id":"mock-..."}`.
4. Open `data/validation/quarterwave_si_sio2_reference.json` and see the same numbers the test asserts against.

When all four work, the foundation phase has its first verifiable rung.

## 11. Out of scope (deferred to later sub-projects)

- HLS port of the C++ kernels (`src/hdl/hls/`, fixed-point validation, Vitis synthesis).
- Hand-written VHDL IP blocks (`src/hdl/vhdl/`, `complex_mult.vhd`, `matrix_chain.vhd`, `sellmeier_lut.vhd`).
- Real Slurm integration (replaces `/mock/slurm/submit` with a `slurm_client.py` service; adds Celery + Redis).
- Additional photonic components (Mach-Zehnder, ring resonator, photodetector, waveguide).
- Apodised gratings, lossy materials (complex `n`), Drude-Lorentz.
- ML surrogates and SHAP explainability tooling.
- Persistent simulation state, twin snapshots, component registry CRUD, auth.
- Lumerical/PyChrono bridges.
- Frontend tests (Vitest/Playwright), drag-and-drop component palette, design-pipeline view.
- Conda recipe for HPC deployment, Windows/macOS CI matrix, production deployment (nginx/Caddy, TLS).

Each of these gets its own design spec when it is taken on.
