# Simulation scope, FPGA readiness, and SME alignment

**Status:** assessment, not an implementation record
**Date:** 2026-10-29
**Basis:** repository evidence at `C:\Dev\photonics_twin`, the v0.1 evaluation
pack in `evaluation/`, and the SPEAR SME Needs Assessment (analysis notebook,
n=24).

---

## 1. Executive summary

The current repository is a **validated single-component simulator and
integration slice**, not a digital twin and not an FPGA implementation.

- **Simulation scope is narrow but credible.** It solves 1-D normal-incidence
  transfer-matrix problems for a lossless Si/SiO2 quarter-wave Bragg grating,
  returns reflectance only, and is validated against the independent Born &
  Wolf oracle. It is fast enough for interactive use on CPU.
- **FPGA capability is design intent only.** There is no HLS build, no VHDL,
  no synthesis report, and no fixed-point validation. The `PHOTONICS_HLS_BUILD`
  branch in `common.hpp` is a placeholder, while the actual kernel uses
  `std::vector`, `std::complex`, `std::cos/sin`, and material pointers. Do not
  describe the platform as FPGA-capable until a gated spike has produced
  synthesis and numerical-equivalence evidence.
- **SME alignment is strongest on access and early-stage feasibility, and
  weakest on the top-ranked value area.** Cost (17/24), limited facility access
  (15/24), and in-house expertise (11/24) are the main barriers. A free,
  browser-based, fast simulator directly addresses the first two and partly
  the third. However, improved sensing/monitoring is the top value area (11/24)
  and the current model cannot yet answer a real sensing question because it
  lacks photoelastic strain, ambient-index, loss, and fabrication effects; its temperature
  model is linear and uncalibrated.
- **Recommended next slice:** extend the Bragg model into a **sensing**
  slice (temperature and geometric strain are done; photoelastic strain, ambient index, tolerance and presets
  remain) before starting FPGA work. It reuses the validated kernel, speaks
  directly to the top SME value area, and produces a demonstrable prototype.

---

## 2. What exists today

| Layer | Implemented | Evidence |
|---|---|---|
| C++ physics core | 1-D TMM, Sellmeier Si/SiO2, uniform Bragg stack | `src/core/` |
| Python bindings | `Material`, `SellmeierCoeffs`, `BraggGrating`, NumPy reflectance | `src/bindings/photonics_core.cpp` |
| Backend | `POST /simulate/tmm/sweep`, `WS /ws/sim`, mock Slurm echo | `src/backend/photonics_twin_app/` |
| Frontend | Parameter sliders, Plotly spectrum, SVG layer stack | `src/frontend/src/` |
| Packaging | scikit-build-core/CMake wheel, Docker Compose, nginx proxy | `pyproject.toml`, `docker/`, `docker-compose.yml` |
| Runtime entry | `.\run.ps1` build/start/health/open | `run.ps1` |
| Validation | Born & Wolf oracle, C++ tests, Python/API/WS tests | `data/validation/`, `tests/`, `evaluation/` |
| CI | C++/Python tests and frontend build | `.github/workflows/ci.yml` |
| HPC | Mock HTTP endpoint only | `routers/mock_slurm.py`, `.github/workflows/hpc-dispatch.yml` |

Explicitly absent: HLS/VHDL source, FDTD or mode solver, Lumerical/PyChrono
bridges, ML surrogates, real Slurm submission, persistence, auth, HDF5 result
storage, design optimisation, and lab-facility integration.

---

## 3. Simulation scope

### 3.1 Physics assumptions

| Dimension | Current model | Consequence |
|---|---|---|
| Geometry | 1-D multilayer stack, plane waves | No waveguides, PICs, diffraction, or 2-D/3-D effects |
| Incidence | Normal incidence | No angle or polarisation dependence |
| Materials | Isotropic, non-magnetic, real refractive index | No absorption, gain, metals, or anisotropy |
| Dispersion | Sellmeier for Si and SiO2 | Valid only inside the fitted ranges |
| Environment | Vacuum incident and substrate media | No fibre, air, substrate, or encapsulation stack |
| Stack design | Uniform quarter-wave pairs | No apodisation, chirp, defects, or arbitrary layer design |
| Output | Reflectance `|r|^2` only | No transmission, phase, field profile, or group delay |
| Temperature | Linear dn/dT plus thermal expansion around 20 C | No calibration or nonlinearity |
| Strain | Geometric thickness scaling; no photoelastic index change | No calibrated gauge or elasto-optic coupling |
| Fabrication | Ideal thicknesses and indices | No tolerance, yield, or process variation |

### 3.2 Parameter envelope

- Centre wavelength: 400-2500 nm (`schemas.py:6`).
- Periods: 2-16, i.e. 4-32 layers (`schemas.py:7`, `MAX_LAYERS = 32`).
- Sweep: 200-3000 nm with 11-4001 points (`schemas.py:10-12`).
- Returned stack metadata: index, material, thickness, `n_at_centre`.

### 3.3 Validation and performance evidence

| Check | Result |
|---|---|
| Peak reflectance vs Born & Wolf at 1550 nm | absolute error `1.4e-11` (budget `1e-3`) |
| Low stop-band edge vs Born & Wolf | `1218.85` vs `1219.34 nm`, error `0.49 nm` (budget `10 nm`) |
| High stop-band edge vs Born & Wolf | `2129.01` vs `2126.73 nm`, error `2.28 nm` (budget `10 nm`) |
| Test suite | 15 Python tests, 8 C++ tests, frontend production build |
| Throughput | about 3k wavelength points/ms at 5 periods; 32 layers stays below 10 ms |

The evidence is strong for the ideal quarter-wave case and weak outside it. The
single validation fixture does not establish accuracy for other centre
wavelengths, material pairs, lossy media, angles, or sensing perturbations.

### 3.4 What the current model can and cannot answer

**Can support now**

- Interactive exploration of quarter-wave Bragg spectra.
- Feasibility conversations about bandwidth, layer count, and index contrast.
- Teaching and awareness: users can see how period count and centre wavelength
  change the response.
- Regression testing of the TMM kernel and the full UI/API/Docker path.
- Reproducible benchmark and validation artifacts.

**Cannot support yet**

- Quantitative sensor design (sensitivity in nm/K, nm/epsilon, nm/RIU).
- Lossy or absorbing materials, metals, or complex refractive indices.
- Angular or polarisation response.
- Waveguide, ring-resonator, MZI, photodetector, or PIC design.
- Fabrication-tolerance and yield analysis.
- Multi-component systems or application-level signal chains.
- Calibration against measured factory or lab data.
- Claims of a "digital twin" in the sense of a calibrated, stateful replica.

---

## 4. FPGA capability

### 4.1 Current state

There is **no FPGA implementation**. The only hardware-related artifact is the
conditional type alias:

```cpp
#ifdef PHOTONICS_HLS_BUILD
    #include <ap_fixed.h>
    using real_t    = ap_fixed<32, 8>;
    using complex_t = std::complex<real_t>;
#else
    using real_t    = double;
    using complex_t = std::complex<double>;
#endif
```

`src/core/include/photonics/common.hpp:9-18`

That branch is not built or tested. The kernel itself is not synthesizable as
written:

- `LayerStack` stores `std::vector<Layer>` (`tmm.hpp:21`) and layers hold
  `const Material*` (`tmm.hpp:11`), which HLS cannot consume as a dynamic
  container of pointers.
- `tmm_sweep` uses `std::complex` and `std::cos/sin` (`tmm.cpp:42-46`).
- Sellmeier evaluation uses runtime division and `std::sqrt`
  (`materials.cpp:11-17`), which are expensive or need explicit HLS math/LUT
  choices.
- The HLS header is included inside `namespace photonics` (`common.hpp:7-10`),
  which needs fixing before a real HLS build.
- There is no `src/hdl/` directory, no VHDL, no HLS testbench, no synthesis
  constraints, no target board, and no Vitis build in CI.

The technical design notes describe targets (`II=1`, unroll factor 4, 32 layers
in BRAM, `ap_fixed<32,8>` and intermediate `<48,16>`) in sections 5.1-5.3. Those
are **design targets, not measured results**.

### 4.2 Is the TMM a good HLS target?

Yes, in principle. The core operation is a chain of 2x2 complex matrix
multiplications with a fixed maximum layer count and a regular wavelength loop.
That maps well to pipelining. But the current implementation would need a
separate HLS-friendly kernel with:

- fixed-size layer arrays and value-type material coefficients;
- explicit fixed-point types and rounding/saturation policy;
- LUT or piecewise Sellmeier evaluation;
- AXI-Stream wavelength input and reflectance output;
- AXI-Lite stack configuration;
- a numerical equivalence test against the double-precision reference.

### 4.3 Why FPGA is not the next priority

The CPU kernel already returns 2001 wavelengths in about 0.6 ms for a 5-period
stack and stays below 10 ms at the 32-layer cap. Interactive SME use cases are
latency-bound at the human scale, not throughput-bound at the FPGA scale. The
business case for FPGA is therefore **batch throughput, power, or embedded
deployment**, not the current UI. A GPU or surrogate path may be cheaper and
faster to deliver.

### 4.4 Gated FPGA spike

Run this only after the sensing slice, or in parallel with a dedicated engineer.

| Gate | Deliverable | Pass criterion |
|---|---|---|
| G0 | Target board, clock, interface, and error budget agreed | Documented and signed off |
| G1 | HLS C++ kernel for a fixed stack and wavelength sweep | C-simulation matches CPU within the agreed tolerance |
| G2 | C synthesis report | Meets latency/II, DSP/BRAM/LUT/FF and clock targets |
| G3 | Co-simulation or host demo | End-to-end sweep produces the expected spectrum |
| G4 | Decision | Adopt HLS, switch to GPU/surrogate, or stop |

Suggested numerical gate: absolute reflectance error <= `1e-3` and peak
wavelength error <= `1 nm` versus the double-precision kernel. Resource and
latency targets must be set per board before G1; without them G2 cannot pass or
fail honestly.

Planning estimate: 6-10 weeks for one engineer with HLS/FPGA experience,
medium-high risk. Vitis is not available on GitHub-hosted runners, so CI needs a
self-hosted runner or a licensed container. **Do not put FPGA capability in
SME-facing or funding claims before G2/G3.**

---

## 5. SME needs evidence

### 5.1 Source and caveats

- Source: `SPEAR_Needs Assessment.pptx`, `SPEAR SME Map - Responses 23.02.26.pptx`,
  and `data_analysis/needs_analysis.ipynb`.
- The analysis notebook uses **n=24** cleaned responses; the latest export has
  24 data rows. Slide 5 of the needs deck reports 25 respondents. Reconcile this
  before external publication.
- The sample is self-selected, Northern Ireland-weighted, and dominated by
  manufacturing and 10-49-employee firms. Treat percentages as directional.
- Only aggregate counts are reproduced in this repository. Respondent-level
  data, open text, and contact details are excluded.

### 5.2 Aggregate findings

| Theme | Finding |
|---|---|
| Sector mix | Manufacturing 13/24, healthcare 3/24, all other sectors 1/24 each |
| Company size | 10-49 employees 13/24; 1-9 employees 9/24; 50-249 2/24 |
| Locations | Antrim 7, Londonderry 7, Tyrone 3, Armagh 2, Down 2, others 3 |
| Technology adoption | Mainstream 13/24, early adopter 10/24, late adopter 1/24 |
| Heard of photonics | Yes 15/24, no 8/24, not sure 1/24 |
| Understanding | Mean 2.5/5, median 2/5 |
| See potential | Yes 15/24, not sure 8/24, no 1/24 |
| Lab facility interest | Yes 14/24 |
| Co-development interest | Yes 11/24, not sure 12/24, no 1/24 |
| Contact request | Yes 16/24 |

**Top barriers**

1. Cost of implementation - 17/24
2. Limited access to R&D or facilities - 15/24
3. Lack of in-house expertise - 11/24

**Top value areas**

1. Improved sensing/monitoring - 11/24
2. Advanced manufacturing - 9/24
3. Miniaturisation of components - 7/24

**Top engagement preferences**

1. Joint R&D projects, publicly funded - 13/24
2. Feasibility studies or prototyping support - 13/24
3. Access to demonstrator technologies - 12/24

**Top support needs**

1. Advanced R&D collaboration - 10/24
2. "I don't know yet" - 9/24
3. Basic understanding/introduction - 8/24

### 5.3 What the open text says, in themes

- Cost and ROI must be clear before SMEs commit time or budget.
- Local or easily commutable facilities matter; university bureaucracy is a
  barrier to easy access.
- Clear IP terms and low administrative burden are prerequisites.
- Short, funded, time-bounded proof-of-concept projects are preferred over
  open-ended academic collaborations.
- Some firms need a concrete explanation of how photonics benefits their
  product, not a technology overview.
- Some lack in-house optical skills and want mentoring or system-integration
  support.
- Demonstrators and access to specialist test equipment are valued.

These themes reinforce the quantitative findings: access, cost, expertise,
clear benefit, and a low-friction route to a prototype.

---

## 6. Alignment matrix

| SME signal (n=24) | Current capability | Alignment | Main gap | Next action | Priority |
|---|---|---|---|---|---|
| Cost 17/24; facility access 15/24 | Free browser UI, CPU simulation, Docker, no licence | Strong for simulation access | No hosted pilot, no cost/ROI model | Publish a free pilot instance and a one-page cost/ROI guide | P0 |
| Feasibility/prototyping 13/24; demonstrators 12/24 | Live sweeps, REST/WS, one-command Docker | Partial | No CSV/JSON export, no save/compare, no preset scenarios | Add export, scenario save/load, and 3-5 demo presets | P0 |
| Sensing/monitoring 11/24 (top value) | Bragg is a sensing element with a linear temperature model | Partial | No strain, ambient-index, loss, tolerance, or calibrated sensitivity | Add strain/ambient-index and tolerance to the sensing slice | P1 |
| Basic understanding 8/24; "don't know yet" 9/24; median understanding 2/5 | Sliders, plot, layer-stack view | Strong/partial | No guided tour, interpretation, or report | Add tutorial presets, tooltips, and a "what this means" panel | P1 |
| Joint R&D 13/24; co-development 11 yes / 12 not sure | Open API, reproducible Docker | Partial | No project scoping, IP template, or engagement workflow | Create an SME engagement pack and IP/terms template | P1 |
| Advanced manufacturing 9/24 | Uniform quarter-wave stack only | Weak | No fabrication tolerance, yield, or process variation | Add tolerance/yield analysis | P2 |
| Miniaturisation 7/24 | No PIC/waveguide/ring/MZI models | Gap | Component library is one device deep | Sequence the component roadmap (ring/MZI/waveguide) | P2 |
| Advanced R&D 10/24 | Validated kernel, tests, API | Partial | No FDTD/Lumerical reference, no HPC, no ML | Add HPC/reference comparison path | P2 |
| Lab facilities 14/24 yes | Not addressed | Gap | No facility information or booking route | Integrate facility/eligibility information with SPEAR partners | P2 |
| Contact interest 16/24 | No lead capture or feedback loop | Gap | No privacy-compliant follow-up workflow | Add a pilot feedback form and contact workflow | P1 |
| Trust and validation | Born & Wolf validation, tests, evaluation pack | Strong | Single ideal fixture | Publish a validation matrix and error budget | P0 |

### 6.1 Alignment verdict

- **Good fit now:** cost/access, feasibility, demonstrators, basic awareness.
- **Promising but not yet credible:** sensing, advanced manufacturing,
  miniaturisation, advanced R&D.
- **Not a software problem alone:** co-development, IP, lab access, and
  commercial terms need SPEAR process work alongside the platform.

The platform is therefore well aligned with the **engagement and awareness**
needs of the SME base, but not yet with the **technical value** they ranked
highest. The sensing extension is the shortest credible route from "interesting
demo" to "useful feasibility study".

### 6.2 Sensitivity sanity check and the RIU limit

The model's temperature sensitivity (`65 pm/K`) is the same order as the
`70-80 pm/degree C` reported for SiO2-clad silicon waveguide Bragg grating
thermometers (NIST, 2015). The geometric strain sensitivity (`1.63 pm/microstrain`)
is higher than the `~1.2 pm/microstrain` of a silica fibre Bragg grating, which
is plausible for a Si/SiO2 quarter-wave stack but is not a direct validation.
The `10 pm` noise case gives `0.153 K` and `6.1 microstrain`, consistent with
the rule of thumb that about `1 pm` wavelength uncertainty corresponds to about
`1 microstrain` (NIST, 2005) and with typical OSA resolution.

This is an **order-of-magnitude check, not a calibration**. Do not quote
`nm/RIU` from the current free-space stack: changing the ambient index mainly
alters boundary reflection, not a guided-mode overlap. A waveguide Bragg
component is required before claiming refractive-index sensing.

References:

- Klimov et al., "On-Chip Silicon Waveguide Bragg Grating Photonic Temperature
  Sensor", Optics Letters (2015), doi:10.1364/OL.40.003934.
- Dyer et al., "Fundamental limits in fiber Bragg grating peak wavelength
  measurements", Proc. SPIE 5855 (2005).
- "Fiber Bragg Grating Sensors toward Structural Health Monitoring in Composite
  Materials", Sensors 14(4), 7394 (2014), doi:10.3390/s140407394.

---

## 7. What is next to complete this

### P0 - make v0.1 defensible (2-4 weeks)

- [x] Write a one-page scope statement: what v0.1 does, what it does not do,
  and why FPGA/digital-twin claims are out of scope.
- [x] Add CSV/JSON export and scenario save/load to the UI.
- [x] Extend the validation matrix beyond one fixture (periods and centre
  wavelengths; Si/SiO2 is still the only supported material pair) and publish
  the error budget.
- [x] Add the evaluation check to CI so the research outputs cannot drift.
- [x] Prepare a short SME pilot pack: demo script, feedback form, cost/ROI
  one-pager, and a privacy notice.
- [ ] Reconcile the 24-vs-25 respondent count before external use. This needs
  the survey owner; it is not a repository change.

**Done when:** a reviewer can state the scope in one minute, reproduce the
evaluation, export a scenario, and run the Docker stack without help.

### P1 - Bragg sensing slice (4-8 weeks)

- [x] Add thermo-optic (`dn/dT`) and thermal-expansion response.
- [x] Add geometric strain (thickness scaling) response.
- [ ] Add photoelastic index change and ambient-index response.
- [x] Report `nm/K` and `pm/microstrain` sensitivity and the stop-band
  centre shift.
- [x] Add measurement-noise-limited temperature/strain resolution.
- [ ] Add a full drift/calibration uncertainty budget; `nm/RIU` is deferred
  to a waveguide component.
- [x] Add seeded Monte Carlo thickness tolerance and yield.
- [ ] Add refractive-index variation and process-specific distributions.
- [x] Add CSV/JSON export.
- [x] Add a batch sweep endpoint.
- [x] Add Telecom, sensing-edge and strain-gauge UI presets.
- [ ] Add a refractive-index preset.
- [x] Sanity-check temperature and strain sensitivity against published
  FBG/silicon values (order of magnitude only).
- [ ] Directly validate against a measured device.

**Done when:** an SME can change a physical input and see a defensible
sensitivity number, not just a shifted spectrum.

### P2 - FPGA decision spike (6-10 weeks, gated)

- [ ] Complete G0-G4 from section 4.4.
- [ ] Publish the synthesis report and the CPU-vs-HLS comparison.
- [ ] Decide HLS vs GPU vs surrogate with a documented business case.

**Done when:** the decision is evidence-based and the phrase "FPGA-capable" is
either supported by a report or removed from the roadmap.

### P3 - platform and engagement (parallel)

- [ ] Replace the mock Slurm endpoint with a real submission path or explicitly
  defer it.
- [ ] Add job status, result storage, and auth before exposing HPC to users.
- [ ] Run co-design sessions with the 16 contactable respondents, starting with
  sensing and manufacturing use cases.
- [ ] Integrate lab-facility information and a booking/eligibility route.
- [ ] Produce training material for the "basic understanding" and "don't know
  yet" segments.

### Definition of done for the current phase

The current phase is complete when:

1. The scope statement and limits are public.
2. The simulation and evaluation are reproducible in Docker and CI.
3. At least one SME-relevant sensing scenario is demonstrable.
4. The FPGA decision is either gated with evidence or explicitly deferred.
5. SME feedback has been collected from a pilot cohort.

---

## 8. Risks and assumptions

| Risk | Impact | Mitigation |
|---|---|---|
| Overclaiming FPGA capability | Credibility and funding risk | Use the G0-G4 gate; say "hardware acceleration path under evaluation" |
| Overclaiming "digital twin" | Mis-set expectations | Describe v0.1 as a simulator/integration slice |
| SME sample bias (n=24, self-selected, NI-weighted) | Weak generalisation | State the caveat; validate with co-design calls |
| 24 vs 25 respondent discrepancy | Reporting inconsistency | Reconcile with the survey owner before publication |
| Sensing value area is broad | Building the wrong sensor model | Run discovery calls; start with temperature/strain/RIU |
| FPGA toolchain/licensing | Schedule slip | Self-hosted runner or licensed container; decide early |
| Cost/access barrier is organisational | Software alone will not solve it | Pair the pilot with a clear cost/ROI and access model |
| No raw data in repo | Limits independent re-analysis | Keep aggregates; link to the source under governance |

---

## 9. Evidence map

| Claim | Evidence |
|---|---|
| Physics and parameter envelope | `src/core/`, `src/backend/photonics_twin_app/schemas.py` |
| Validation and performance | `evaluation/outputs/validation_vs_analytic.json`, `benchmark.json`, `summary.md` |
| FPGA intent vs implementation | `src/core/include/photonics/common.hpp:9-18`, `tmm.hpp`, `tmm.cpp`, absence of `src/hdl/` |
| Platform integration | `src/frontend/`, `src/backend/`, `docker/`, `run.ps1` |
| SME aggregates | `evaluation/outputs/sme_needs_summary.json`, `data_analysis/needs_analysis.ipynb` |
| SME narrative | `SPEAR_Needs Assessment.pptx`, `SPEAR SME Map - Responses 23.02.26.pptx` |
| Out-of-scope items | `docs/superpowers/specs/2026-04-29-bragg-feasibility-prototype-design.md` section 11 |
| FPGA targets | `docs/photonics_twin_technical_design_notes.md` sections 5.1-5.3 |
