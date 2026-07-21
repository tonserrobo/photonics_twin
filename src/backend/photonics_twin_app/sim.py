"""Orchestration between the FastAPI layer and the C++ photonics_core module."""
import json
import os
import time
from functools import lru_cache
from pathlib import Path

import numpy as np

import photonics_core as pc
from photonics_twin_app.schemas import BraggParams, Sweep

# parents[3] only resolves in the source tree; once installed to site-packages it
# points at the interpreter's lib dir. PHOTONICS_DATA_DIR is how containers say where
# data actually landed.
DATA_DIR = Path(os.environ.get("PHOTONICS_DATA_DIR", Path(__file__).resolve().parents[3] / "data"))
MATERIALS_DIR = DATA_DIR / "materials"

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
