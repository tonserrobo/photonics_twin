# Photonics Digital Twin Platform — Technical Design Document

**SPEAR HPC Programme | DRAFT v0.1 | March 2026**

---

## 1. Executive Summary

This document defines the technical architecture for the Photonics Digital Twin Platform being developed under the SPEAR HPC programme. The platform provides a composable simulation environment for photonic sensor design, application-level integration, and factory-scale digital twin deployment.

The system combines high-performance C++ physics kernels with a Python/FastAPI backend and React frontend, connected to HPC infrastructure via Slurm job scheduling and GitHub Actions CI/CD pipelines. Physics kernels are designed for dual deployment: software simulation and FPGA hardware acceleration via Vitis HLS.

The programme spans four years across two major phases: a foundation phase (Years 1–2) establishing validated simulation infrastructure and composable component models, followed by a factory integration phase (Years 3–4) incorporating real-world data, physics-informed machine learning surrogates, and closed-loop digital twin refinement.

---

## 2. Programme Roadmap

### 2.1 Years 1–2: Foundation Model

The foundation phase establishes the core simulation platform, validated physics models, and end-to-end infrastructure connecting the HPC sandbox to user-facing tools.

#### HPC Sandbox Infrastructure

The primary infrastructure goal is linking the HPC environment to a sandbox partition accessible through a CI/CD pipeline:

1. GitHub push or pull request triggers a GitHub Actions workflow.
2. The Actions workflow makes an API call to the Slurm job scheduler on the HPC cluster.
3. Slurm allocates resources within the designated sandbox partition.
4. The simulation executes on allocated resources.
5. Results are pushed back to the repository or an interactive dashboard.

**Initial implementation:** The first milestone targets a notification-only endpoint — confirming that the GitHub Actions to Slurm dispatch pathway is functional before running full simulations. This de-risks the integration early.

#### Interactive Simulation UI

Users require an interactive frontend for parameter exploration and real-time visualisation of photonic component behaviour. The interface will support parameter sweeps, spectral response visualisation, and component composition.

**Technology choice:** React frontend with Plotly/Three.js visualisation, served by a FastAPI backend. This replaces the initial Gradio/Flask consideration to provide better WebSocket support for live simulation updates and auto-generated OpenAPI documentation.

#### Physics Simulation Backend

The simulation backend supports multiple compute pathways of varying fidelity and latency:

- **Ansys Lumerical API:** Full-fidelity electromagnetic simulation (FDTD, MODE). Used as the reference standard for validation. Dispatched to HPC for computationally intensive runs.
- **PyChrono:** Lightweight multiphysics environment for mechanical/thermal coupling. Requires exploration of C++/Python interoperability for integration with optical kernels.
- **Custom C++ kernels:** Purpose-built photonics compute library (transfer matrix method, mode solvers, spectral response) exposed to Python via pybind11. Designed for millisecond-scale interactive evaluation.
- **ML surrogates:** Aggregated/composite machine learning models trained from the above, serving as approximate fast-compute design blocks with explainability (xAI) requirements. These replace full VHDL-synthesised designs for rapid design-space exploration.

#### Feasibility Prototype

A feasibility prototype targeting the first month of the programme will demonstrate end-to-end pipeline viability:

- A single photonic component model (e.g., Bragg grating) implemented as a C++ kernel with Python bindings.
- A minimal FastAPI backend accepting parameters and returning simulation results.
- A basic React frontend for parameter input and spectral response visualisation.
- A GitHub Action triggering a dummy Slurm job submission (notification-only).

#### Foundation Deliverable

The Year 2 deliverable is a well-tuned foundation model: a validated set of photonic component simulations with defined accuracy metrics, accessible through the interactive UI and integrated with the HPC pipeline.

### 2.2 Year 3: Factory Integration & Surrogate Modelling

#### Digital Twin Factory Integration

The transition from simulation to factory-integrated digital twin involves two parallel workstreams:

**Photonic sensor models:** These do not require real factory sensor data for initial development. Synthetic sensor models will be built in Years 1–2 using physics-based priors (transfer matrices, coupled mode theory), validated against published literature, and calibrated against SMDH data when available. Ideally a photonics specialist would contribute to this development, though the core work is an exercise in collating and converting existing models into the repository.

**SMDH data access:** Ethical approvals for accessing real factory data from SMDH will be initiated toward the end of Year 1. Research Office engagement is required for data governance agreements. Early initiation is critical as ethics applications can take 6–12 months.

#### Physics-Informed Machine Learning

The programme employs a hybrid surrogate modelling approach: physics-based machine learning models that approximate machine behaviour, using optimal-case outputs to tune a feedback loop for the digital twin over the four-year programme.

Key considerations:

- **Surrogate scope:** Distinguish between surrogates of the simulation (neural operators making C++ kernels faster) and surrogates of the physical process (capturing phenomena the simulation misses). These require different architectures: Fourier Neural Operators / DeepONet for the former, physics-constrained system identification for the latter.
- **Validation methodology:** Define quantitative acceptance criteria for surrogate model fidelity. Metrics include RMSE against reference simulations, spectral fidelity measures, and defined error budgets for each sensor model.
- **Recalibration protocol:** The feedback loop implies model drift as the twin diverges from physical reality over time. A structured recalibration protocol (triggers, data requirements, frequency) must be defined and documented.
- **Explainability (xAI):** All surrogate models require interpretability tooling (SHAP analysis, feature importance) to maintain trust and enable design insight extraction.

#### Virtual Sensor Inputs

Virtual inputs enable the digital twin to simulate sensor behaviour under conditions not yet physically tested. This supports design-space exploration and predictive maintenance scenarios within the factory integration context.

---

## 3. System Architecture

### 3.1 Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    React Frontend                        │
│         (Parameter UI, Spectral Viz, Job Status)         │
└────────────────────────┬────────────────────────────────┘
                         │ WebSocket / REST
┌────────────────────────▼────────────────────────────────┐
│                  FastAPI Backend                          │
│        (Job Orchestration, Auth, API Gateway)             │
└───┬──────────────┬──────────────┬───────────────────────┘
    │              │              │
    ▼              ▼              ▼
┌────────┐  ┌───────────┐  ┌──────────────┐
│ C++    │  │ Lumerical  │  │ Slurm HPC    │
│ Kernels│  │ / Cadence  │  │ Job Dispatch │
│(pybind)│  │ API Bridge │  │              │
└────────┘  └───────────┘  └──────────────┘
```

The platform follows a layered architecture separating concerns across frontend presentation, API orchestration, and heterogeneous compute backends. The system is designed for composability at every level: components can be chained in simulation, compute backends can be swapped transparently, and the digital twin state is serialisable for snapshots and versioning.

### 3.2 Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | React + TypeScript, Plotly, Three.js | Interactive parameter UI, spectral visualisation, job status dashboard |
| Backend | FastAPI + Celery + Redis | API gateway, async job orchestration, WebSocket live updates |
| Compute | C++17 via pybind11 | Physics kernels: TMM, FDTD, mode solvers, spectral response |
| HLS/FPGA | VHDL + Vitis HLS (C++) | Hardware-accelerated kernels for production deployment |
| Simulation | Lumerical API, PyChrono | Full-fidelity reference simulations, multiphysics coupling |
| ML | PyTorch + scikit-learn + SHAP | Surrogate models, training pipelines, explainability tooling |
| HPC | Slurm + GitHub Actions | Job scheduling, CI/CD triggers, sandbox partition management |
| Data | HDF5 + PostgreSQL | Simulation results storage, metadata, component registry |

### 3.3 Language Boundaries

| Language | Domain | Rationale |
|----------|--------|-----------|
| C++17 | Physics kernels, HLS source | Performance-critical compute; direct pathway to Vitis HLS synthesis; natural fit for fixed-point arithmetic |
| Python | Backend API, ML training, orchestration | Ecosystem (PyTorch, scipy, Lumerical API); rapid prototyping; pybind11 bridge to C++ kernels |
| TypeScript | Frontend UI | Type safety for complex simulation state; React ecosystem; auto-generated API client from OpenAPI |
| VHDL | Hand-optimised FPGA IP | Fine-grained control for pipelined architectures (complex multipliers, matrix chains); industry standard for verification |

The C++ choice is strategically motivated by dual-deployment capability: the same algorithmic code serves both high-performance software simulation and, with HLS pragmas and fixed-point types, FPGA hardware acceleration via Vitis HLS. This eliminates the need for algorithm re-implementation when transitioning from simulation to hardware.

---

## 4. Photonic Component Model

### 4.1 Design Philosophy

The platform serves two distinct but connected use cases:

- **Sensor design:** Modelling the photonic sensor itself — spectral response, sensitivity, noise characteristics, photochromatic material properties, and wavelength-dependent behaviour.
- **Application integration:** Modelling how sensors behave within larger systems — interfacing components, signal chains, environmental factors, and factory-level process interactions.

The digital twin must operate at both levels, requiring a composable component architecture where each photonic device exposes a standard interface: input spectrum, output response, noise model, and configurable operating parameters. Components can be chained for application-level simulation without modification.

### 4.2 Component Interface

Every photonic component implements a base C++ interface (`Component` class) providing:

| Method | Purpose |
|--------|---------|
| `evaluate()` | Compute full spectral response for a given input spectrum (wavelength, complex field pairs) |
| `transfer()` | Evaluate transmission at a single wavelength — optimised for fast parameter sweeps and interactive use |
| `set_param()` / `get_params()` | Runtime configuration of component parameters (dimensions, materials, temperature, etc.) |
| `get_param_metadata()` | Returns parameter names, ranges, units, and descriptions — drives automatic UI generation |
| `add_noise()` | Apply realistic noise model for sensor-level simulation at a given SNR |
| `serialise()` / `deserialise()` | State persistence for digital twin snapshots and version control |

This interface enables three key capabilities: composable pipelines (chain components for application-level simulations), uniform surrogate training (sample any component's `evaluate()` to generate ML training data), and a clear HLS export pathway (each `transfer()` function is a candidate for FPGA synthesis).

### 4.3 Photochromatic Physics Requirements

The physics library must simulate wavelength-dependent optical properties for photonic sensors:

- **Wavelength-dependent refractive indices:** Sellmeier equation models for transparent dielectrics (SiO₂, Si₃N₄, LiNbO₃); Drude-Lorentz models for metals and lossy materials.
- **Absorption spectra:** Material-specific absorption as a function of wavelength, including photochromic materials with switchable optical states.
- **Thin-film optics:** Fresnel equations and Transfer Matrix Method for multilayer structures — the workhorse for Bragg gratings, anti-reflection coatings, and Fabry-Perot cavities.
- **Chromatic dispersion:** Group velocity dispersion parameters for pulse propagation and bandwidth analysis.
- **Thermo-optic effects:** Temperature-dependent refractive index changes (dn/dT) for thermal sensitivity modelling.

### 4.4 Component Library

| Component | Physics Model | HLS Candidate |
|-----------|--------------|---------------|
| Bragg Grating | Transfer Matrix Method (periodic multilayer) | Yes — matrix chain multiplication maps directly to pipelined FPGA architecture |
| Mach-Zehnder Interferometer | Coupled-mode theory, interference equations | Yes — arithmetic-intensive, regular data flow |
| Ring Resonator | Coupled-mode theory, transfer function | Yes — lorentzian response evaluation |
| Photodetector | Responsivity model, noise equivalent power | Partial — noise generation may require software |
| Waveguide | Mode solver, propagation loss, dispersion | Mode solver is iterative; propagation is HLS-suitable |

---

## 5. FPGA Acceleration Strategy

### 5.1 C++ to Hardware Pipeline

The C++ kernel design explicitly targets Vitis HLS synthesis. Each kernel exists in two forms:

- **Software version** (`src/core/`): Uses standard C++17 types (`std::complex<double>`, `std::vector`). Optimised for CPU execution and numerical validation.
- **HLS version** (`src/hdl/hls/`): Uses Xilinx fixed-point types (`ap_fixed`), HLS streams, and synthesis pragmas. Structurally equivalent algorithm with hardware-appropriate data types.

Integration tests (`test_cpp_vs_hls.py`) validate numerical equivalence between the two implementations within a defined error tolerance, ensuring the FPGA-accelerated version produces trustworthy results.

### 5.2 Transfer Matrix Method as HLS Target

The TMM is the primary HLS acceleration target due to its computational structure: it is fundamentally a chain of 2×2 complex matrix multiplications, which FPGAs can pipeline efficiently. The HLS kernel uses AXI-Stream interfaces for wavelength sweep input and reflectance output, with AXI-Lite for layer stack configuration.

Key HLS design decisions:

- **Fixed-point precision:** `ap_fixed<32,8>` for general computation, `ap_fixed<48,16>` for intermediate products. Precision validated against double-precision C++ reference.
- **Pipeline target:** One reflectance result per clock cycle (II=1) for the wavelength sweep loop, with layer loop unrolled by factor of 4.
- **Resource strategy:** Layer stack stored in BRAM with complete array partitioning for parallel access. Maximum 32 layers per stack.

### 5.3 VHDL Components

Hand-written VHDL is used for performance-critical IP blocks where HLS-generated RTL is insufficient:

- **Complex multiplier (`complex_mult.vhd`):** Optimised complex number multiplication using DSP48 primitives with minimal resource usage.
- **Matrix chain (`matrix_chain.vhd`):** Pipelined 2×2 matrix multiplication chain for TMM layer accumulation.
- **Sellmeier LUT (`sellmeier_lut.vhd`):** Pre-computed material refractive index look-up table for real-time wavelength-dependent evaluation.

---

## 6. Surrogate Modelling & Machine Learning

### 6.1 Surrogate Architecture

Two distinct surrogate types are planned:

- **Simulation surrogates:** Neural approximations of the C++ physics kernels (e.g., a neural network that predicts TMM spectral response given layer parameters). Architectures under consideration include Fourier Neural Operators and DeepONet. These accelerate design-space exploration.
- **Process surrogates:** Models trained on real factory data (Year 3 onwards) that capture physical phenomena the simulation may miss. These use physics-constrained system identification and form the basis of the feedback loop for twin calibration.

### 6.2 Training Data Generation

Training data is generated by systematically sampling the C++ kernel parameter space. The Component interface's uniform `set_param()` / `evaluate()` contract means any component can be sampled using the same pipeline: Latin Hypercube Sampling over the parameter metadata ranges, batch evaluation via the C++ kernels, and storage in HDF5 format.

### 6.3 Explainability Requirements

All surrogate models must provide interpretability through SHAP (SHapley Additive exPlanations) analysis and feature importance metrics. This is not optional — design engineers need to understand *why* a surrogate predicts a particular spectral response to extract actionable design insights, not merely receive a black-box prediction.

### 6.4 Validation & Error Budgets

Surrogate model acceptance requires meeting quantitative thresholds defined before training begins:

| Metric | Target | Measured Against |
|--------|--------|-----------------|
| Spectral RMSE | < 1% of peak response | C++ kernel reference output |
| Peak wavelength error | < 0.1 nm | C++ kernel / Lumerical |
| Inference latency | < 1 ms per evaluation | Measured on target hardware |
| Training coverage | > 95% of parameter space | Latin Hypercube sampling density |

These thresholds define when the foundation model is considered "well-tuned" and when the programme can credibly transition from foundation to factory integration.

---

## 7. CI/CD Pipeline & HPC Integration

### 7.1 GitHub Actions Workflows

| Workflow | Trigger | Actions |
|----------|---------|---------|
| `ci.yml` | Push / PR to main, develop | Build C++ kernels, run Google Test and pytest suites, lint Python and TypeScript, build frontend |
| `hpc-dispatch.yml` | Git tag (`sim-*`) or manual dispatch | SSH to HPC cluster, submit Slurm job with specified config YAML and partition, report job ID |
| `deploy-docs.yml` | Push to main (docs/ changed) | Build and publish project documentation |

### 7.2 HPC Job Lifecycle

1. **Trigger:** GitHub Action or direct API call from the FastAPI backend.
2. **Submission:** Slurm `sbatch` with specified partition (sandbox for development, production for validated runs).
3. **Execution:** Simulation runs on allocated nodes using containerised worker images (Docker).
4. **Monitoring:** WebSocket connection from frontend polls job status; Celery task tracks completion.
5. **Results:** Output written to HDF5, pushed to results database, dashboard updated via WebSocket notification.

**Timeout consideration:** GitHub Actions has a 6-hour timeout on standard runners. The workflow submits the Slurm job and returns immediately — it does not block waiting for simulation completion. Job status is tracked asynchronously through the backend API.

---

## 8. Repository Structure

```
photonics-twin/
├── .github/workflows/          # CI, HPC dispatch, docs deploy
├── CMakeLists.txt              # Top-level C++ build
├── pyproject.toml              # Python package (PEP 621)
├── docker-compose.yml          # Full stack local dev
│
├── src/
│   ├── core/                   # C++ physics kernels (TMM, FDTD, modes, materials)
│   │   ├── include/photonics/  # Headers (component.hpp, tmm.hpp, materials.hpp, ...)
│   │   ├── src/                # Implementations
│   │   └── components/         # Bragg grating, MZI, ring resonator, photodetector, waveguide
│   ├── bindings/               # pybind11 bridge (thin layer, no business logic)
│   ├── backend/                # FastAPI app (routers, services, workers, models)
│   ├── frontend/               # React + TypeScript (components, hooks, API client)
│   ├── hdl/                    # VHDL IP blocks + Vitis HLS kernels + testbenches
│   └── models/                 # ML surrogates, training pipelines, xAI, validation
│
├── simulations/                # Config YAMLs, Lumerical templates, Slurm job scripts
├── data/                       # Material databases, validation references, synthetic training data
├── tests/                      # C++ (GTest), Python (pytest), HDL (GHDL), integration
├── docker/                     # Dockerfiles (backend, frontend, HPC worker, dev)
├── docs/                       # Architecture, component interface guide, HLS workflow, ADRs
└── notebooks/                  # Jupyter: material props, TMM validation, surrogate training
```

---

## 9. Risks & Mitigations

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| SMDH ethical approval delays | High | Initiate process end of Year 1. Build synthetic sensor models in parallel so Year 3 work is calibration, not creation. |
| C++ kernel development scope | Medium | Start with TMM only (well-characterised, literature-validated). Expand to FDTD/mode solvers only after foundation is proven. |
| HLS numerical divergence | Medium | Integration tests comparing C++ double-precision against HLS fixed-point. Define acceptable error tolerance before synthesis. |
| Lumerical licensing on HPC | Medium | Clarify licence server configuration early. Use C++ kernels for interactive use; reserve Lumerical for batch validation on HPC. |
| Surrogate model drift | High (Yr 3+) | Define recalibration protocol with triggers, data requirements, and frequency. Budget for ongoing validation against physical measurements. |
| GitHub Actions ↔ Slurm integration | Low | Phase 1 targets notification-only endpoint. Full integration requires SSH/API access to HPC — confirm network policy early. |

---

## 10. Immediate Next Steps

| # | Action | Owner / Notes |
|---|--------|---------------|
| 1 | Initialise GitHub repository with scaffold structure, CMakeLists, pyproject.toml, and CI workflow. | Lead developer |
| 2 | Implement Bragg grating C++ component with pybind11 bindings and TMM spectral sweep. | C++ / photonics lead |
| 3 | Stand up minimal FastAPI backend with `/simulate/tmm/sweep` endpoint. | Backend developer |
| 4 | Build basic React frontend with parameter sliders and Plotly spectral plot. | Frontend developer |
| 5 | Create GitHub Action that triggers a notification-only Slurm endpoint. | DevOps / HPC admin |
| 6 | Confirm HPC sandbox partition access, network policies, and Slurm API availability. | HPC admin |
| 7 | Draft SMDH data access ethics application (for submission end of Year 1). | PI / Research Office |
| 8 | Define validation methodology and error budget thresholds for foundation model acceptance. | Photonics lead / PI |
