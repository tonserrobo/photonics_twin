"""Orchestration between the FastAPI layer and the C++ photonics_core module."""
import json
import os
import time
from functools import lru_cache
from pathlib import Path

import numpy as np

import photonics_core as pc
from photonics_twin_app.schemas import BraggParams, Sweep

# parents[3] resolves in the source tree; once installed to site-packages it
# points at the interpreter's lib dir. PHOTONICS_DATA_DIR is how containers say
# where data landed, and cwd/data covers a non-editable install run from the repo
# root (CI).
def _default_data_dir() -> Path:
    source_tree = Path(__file__).resolve().parents[3] / "data"
    repo_cwd = Path.cwd() / "data"
    for candidate in (source_tree, repo_cwd):
        if (candidate / "materials").is_dir():
            return candidate
    return source_tree

_env_data_dir = os.environ.get("PHOTONICS_DATA_DIR")
DATA_DIR = Path(_env_data_dir) if _env_data_dir else _default_data_dir()
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
