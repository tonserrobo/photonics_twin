# SPEAR Photonics Digital Twin

## Project structure

```
photonics-twin/
│
├── .github/
│   └── workflows/
│       ├── ci.yml                          # Build & test on push/PR
│       ├── hpc-dispatch.yml                # Trigger Slurm job from PR/tag
│       └── deploy-docs.yml                 # Auto-publish docs
│
├── CMakeLists.txt                          # Top-level C++ build
├── pyproject.toml                          # Python package (PEP 621)
├── docker-compose.yml                      # Full stack local dev
├── README.md
│
├── src/
│   │
│   ├── core/                               # ── C++ PHYSICS KERNELS ──
│   │   ├── CMakeLists.txt
│   │   ├── include/
│   │   │   └── photonics/
│   │   │       ├── common.hpp              # Shared types, constants
│   │   │       ├── materials.hpp           # Sellmeier, Drude-Lorentz
│   │   │       ├── tmm.hpp                 # Transfer Matrix Method
│   │   │       ├── mode_solver.hpp         # Waveguide mode analysis
│   │   │       ├── fdtd.hpp                # Finite-Difference Time-Domain
│   │   │       ├── spectral.hpp            # Spectral response & chromatic
│   │   │       └── component.hpp           # Base component interface
│   │   ├── src/
│   │   │   ├── materials.cpp
│   │   │   ├── tmm.cpp
│   │   │   ├── mode_solver.cpp
│   │   │   ├── fdtd.cpp
│   │   │   ├── spectral.cpp
│   │   │   └── component.cpp
│   │   └── components/                     # Composable photonic devices
│   │       ├── bragg_grating.hpp / .cpp
│   │       ├── mach_zehnder.hpp / .cpp
│   │       ├── ring_resonator.hpp / .cpp
│   │       ├── photodetector.hpp / .cpp
│   │       └── waveguide.hpp / .cpp
│   │
│   ├── bindings/                           # ── PYBIND11 BRIDGE ──
│   │   ├── CMakeLists.txt
│   │   ├── bind_materials.cpp
│   │   ├── bind_tmm.cpp
│   │   ├── bind_components.cpp
│   │   └── photonics_core.cpp              # Module entry point
│   │
│   ├── backend/                            # ── FASTAPI APPLICATION ──
│   │   ├── app/
│   │   │   ├── __init__.py
│   │   │   ├── main.py                     # FastAPI app, CORS, lifespan
│   │   │   ├── config.py                   # Pydantic BaseSettings
│   │   │   ├── routers/
│   │   │   │   ├── simulate.py             # POST /simulate (quick C++ eval)
│   │   │   │   ├── hpc_jobs.py             # POST /jobs (Slurm dispatch)
│   │   │   │   ├── components.py           # CRUD for component library
│   │   │   │   ├── twins.py                # Digital twin state & config
│   │   │   │   └── ws.py                   # WebSocket for live updates
│   │   │   ├── services/
│   │   │   │   ├── simulation.py           # Orchestrates C++ kernel calls
│   │   │   │   ├── slurm_client.py         # Slurm REST/SSH dispatch
│   │   │   │   ├── lumerical_bridge.py     # Lumerical API wrapper
│   │   │   │   └── surrogate.py            # ML surrogate inference
│   │   │   ├── models/
│   │   │   │   ├── schemas.py              # Pydantic request/response
│   │   │   │   └── component_registry.py   # Component definitions
│   │   │   └── workers/
│   │   │       └── celery_tasks.py         # Async task queue
│   │   └── requirements.txt
│   │
│   ├── frontend/                           # ── REACT UI ──
│   │   ├── package.json
│   │   ├── vite.config.ts
│   │   ├── src/
│   │   │   ├── App.tsx
│   │   │   ├── components/
│   │   │   │   ├── SimulationCanvas.tsx    # Main vis (Plotly/Three.js)
│   │   │   │   ├── ParameterPanel.tsx      # Sliders for component params
│   │   │   │   ├── SpectralPlot.tsx        # Wavelength response charts
│   │   │   │   ├── ComponentPalette.tsx    # Drag-and-drop library
│   │   │   │   ├── JobMonitor.tsx          # HPC job status dashboard
│   │   │   │   ├── TwinViewer.tsx          # Digital twin state vis
│   │   │   │   └── DesignPipeline.tsx      # Application-level builder
│   │   │   ├── hooks/
│   │   │   │   ├── useSimulation.ts        # WebSocket sim state
│   │   │   │   └── useJobStatus.ts         # Poll/subscribe HPC jobs
│   │   │   └── api/
│   │   │       └── client.ts               # Auto-gen from OpenAPI spec
│   │   └── tests/
│   │
│   ├── hdl/                                # ── VHDL & HLS ACCELERATION ──
│   │   ├── README.md
│   │   ├── vhdl/
│   │   │   ├── tmm_pipeline/
│   │   │   │   ├── tmm_core.vhd
│   │   │   │   ├── complex_mult.vhd
│   │   │   │   ├── matrix_chain.vhd
│   │   │   │   └── tmm_top.vhd             # Top-level w/ AXI interface
│   │   │   ├── spectral_engine/
│   │   │   │   ├── spectral_sweep.vhd
│   │   │   │   └── sellmeier_lut.vhd       # Material LUT
│   │   │   └── testbench/
│   │   │       ├── tb_tmm_core.vhd
│   │   │       └── tb_spectral_sweep.vhd
│   │   ├── hls/                            # Vitis HLS (C++ → RTL)
│   │   │   ├── tmm_hls/
│   │   │   │   ├── tmm_kernel.cpp          # HLS-synthesisable TMM
│   │   │   │   ├── tmm_kernel.hpp
│   │   │   │   ├── tmm_tb.cpp
│   │   │   │   └── directives.tcl
│   │   │   ├── mode_solver_hls/
│   │   │   │   └── mode_kernel.cpp / .hpp
│   │   │   └── common/
│   │   │       ├── fixed_point.hpp         # ap_fixed type definitions
│   │   │       └── complex_ops.hpp         # Complex arith for HLS
│   │   ├── constraints/
│   │   │   └── timing.xdc
│   │   └── scripts/
│   │       ├── synth_vivado.tcl
│   │       └── run_hls.tcl
│   │
│   └── models/                             # ── ML SURROGATES ──
│       ├── surrogates/
│       │   ├── base.py                     # Abstract surrogate interface
│       │   ├── tmm_surrogate.py
│       │   ├── spectral_surrogate.py
│       │   └── factory_model.py            # Yr3: factory process
│       ├── training/
│       │   ├── generate_training_data.py   # Sample C++ → datasets
│       │   ├── train_surrogate.py
│       │   └── configs/
│       ├── explainability/                 # xAI
│       │   ├── shap_analysis.py
│       │   └── feature_importance.py
│       └── validation/
│           ├── compare_surrogate_vs_cpp.py
│           └── metrics.py
│
├── simulations/
│   ├── examples/
│   │   ├── bragg_grating_sweep.yaml
│   │   ├── mzi_sensor_response.yaml
│   │   └── ring_resonator_tuning.yaml
│   ├── lumerical/
│   │   └── templates/                      # .lsf / .fsp templates
│   └── slurm/
│       ├── job_template.sh
│       └── sandbox_partition.conf
│
├── data/
│   ├── materials/
│   │   ├── sellmeier_coefficients.json
│   │   └── absorption_spectra/
│   ├── validation/                         # Published reference results
│   └── synthetic/                          # Generated training data
│
├── tests/
│   ├── cpp/                                # Google Test
│   │   ├── test_tmm.cpp
│   │   ├── test_materials.cpp
│   │   └── test_components.cpp
│   ├── python/                             # pytest
│   │   ├── test_bindings.py                # C++ ↔ Python bridge
│   │   ├── test_api.py                     # FastAPI endpoints
│   │   └── test_surrogates.py
│   ├── hdl/                                # GHDL/ModelSim
│   │   └── run_testbenches.sh
│   └── integration/
│       ├── test_cpp_vs_hls.py              # C++ ↔ HLS numerical match
│       └── test_surrogate_vs_cpp.py        # ML ↔ C++ comparison
│
├── docker/
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   ├── Dockerfile.hpc-worker
│   └── Dockerfile.dev
│
├── docs/
│   ├── architecture.md
│   ├── component-interface.md              # How to add components
│   ├── hls-workflow.md
│   ├── validation-methodology.md
│   └── adr/                                # Architecture Decision Records
│       ├── 001-cpp-for-physics-kernels.md
│       ├── 002-pybind11-over-ctypes.md
│       └── 003-fastapi-over-flask.md
│
└── notebooks/
    ├── 01_material_properties.ipynb
    ├── 02_tmm_validation.ipynb
    ├── 03_surrogate_training.ipynb
    └── 04_hls_comparison.ipynb
```
