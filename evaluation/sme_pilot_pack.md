# SME pilot pack - v0.1 Bragg simulator

**Status:** draft for internal review. Replace the bracketed placeholders and
have the privacy text approved by the SPEAR project before external use.

## 1. Purpose

A 20-30 minute structured walkthrough with an SME. The goal is to test whether
the v0.1 simulator and its framing are useful for early feasibility work, not to
sell a product or imply a complete digital twin.

## 2. Demo script

Preconditions: Docker is running, `.\run.ps1` has brought the stack up, and the
default scenario loads at `http://localhost:5173`.

1. **Context (2 min).** Single-component Bragg grating simulator. It models a
   1-D, normal-incidence, lossless Si/SiO2 quarter-wave stack and returns
   reflectance. It is not an FPGA implementation or a calibrated digital twin.
2. **Baseline (3 min).** Show the default 1550 nm, 15-period stack. Point out
   the high-reflectance band, the layer stack, and the compute time.
3. **Parameter sensitivity (5 min).** Move periods from 2 to 16, then change the
   design centre between 1310, 1550, and 2000 nm. Explain the reflectance and
   bandwidth trade-off.
4. **Export and reuse (3 min).** Export the spectrum as CSV, save the scenario,
   then load it again. Explain that a scenario is just parameters plus a sweep.
5. **Map to the SME (5 min).** Ask which of the top value areas is closest:
   sensing/monitoring, advanced manufacturing, or miniaturisation. If the answer
   is outside the current model, say so and record it as a gap.
6. **Limits (2 min).** No temperature, strain, ambient-index, loss, angle,
   polarisation, fabrication tolerance, or PIC models yet. FPGA is under
   evaluation.
7. **Feedback (5 min).** Complete the form below.

## 3. Feedback form

Keep responses in SPEAR's approved survey/CRM system, not in this repository.

1. Which value area is closest to your business? (sensing/monitoring, advanced
   manufacturing, miniaturisation, other)
2. How understandable was the demo? (1 = not at all, 5 = very clear)
3. Did it answer a question you actually have? (yes / partly / no)
4. Which missing capability would make it useful? (temperature, strain,
   ambient index, loss, angle, PIC/waveguide, fabrication tolerance, batch
   export, other)
5. Would you use a free hosted version for early exploration? (yes / not sure /
   no)
6. What would make you trust the numbers? (validation, comparison with
   measurement, uncertainty, source code, other)
7. Would you join a 30-minute co-design call? (yes / no)
8. Anything else?

## 4. Cost/ROI one-pager (template)

- **What the pilot costs:** no software licence for v0.1; the main cost is
  staff time for the session and follow-up.
- **What it replaces:** some early design-space screening before lab, fab, or
  full-wave simulation time.
- **What it cannot replace:** measurement, full-wave/FDTD simulation, process
  validation, or a calibrated twin.
- **ROI framing:** time saved per explored scenario multiplied by loaded staff
  cost, plus avoided blind trials. SPEAR should fill in the rates and a worked
  example.
- **Next step:** if the pilot is useful, scope a short, time-bounded proof of
  concept with clear deliverables and IP terms.

## 5. Privacy notice (template)

- The simulator does not collect personal data. Parameters stay in the browser
  unless the user exports them.
- Feedback is collected through SPEAR's approved form. State the purpose,
  retention period, lawful basis, and contact route.
- Do not upload confidential designs to a shared instance without a written
  agreement. Use synthetic or representative parameters for the pilot.
- Replace this section with the approved SPEAR privacy text before use.

## 6. Success criteria for the pilot

- 3-5 sessions with SMEs in sensing or manufacturing.
- At least 3 of 5 participants can explain the value in their own words.
- At least 2 concrete missing-capability requests that map to P1/P2.
- A feedback log exists outside the repo, with no personal data committed here.
