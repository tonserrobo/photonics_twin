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
        data = json.load(fh)
    c = data["coeffs"]
    thermal = data.get("thermal", {})
    return pc.Material(name, pc.SellmeierCoeffs(
        c["B1"], c["B2"], c["B3"], c["C1"], c["C2"], c["C3"]
    ), pc.ThermalCoeffs(
        thermal.get("dn_dT_per_K", 0.0), thermal.get("cte_per_K", 0.0)
    ))

def _stop_band_edges(wavelengths, reflectance, centre_nm, level=0.5):
    """Low/high R>=level crossings around the design wavelength, interpolated."""
    start = int(np.argmin(np.abs(wavelengths - centre_nm)))
    i = start
    while i > 0 and reflectance[i] >= level:
        i -= 1
    j = start
    while j < len(reflectance) - 1 and reflectance[j] >= level:
        j += 1
    if not (reflectance[i] < level < reflectance[i + 1]
            and reflectance[j] < level < reflectance[j - 1]):
        return None

    def crossing(a, b):
        return float(
            wavelengths[a]
            + (level - reflectance[a])
            * (wavelengths[b] - wavelengths[a])
            / (reflectance[b] - reflectance[a])
        )

    return crossing(i, i + 1), crossing(j, j - 1)


def _edges_at(high, low, params, temperature_c):
    g = pc.BraggGrating(high, low, params.centre_nm, params.periods)
    g.set_temperature_c(temperature_c)
    # Wider than the stop band so both edges are inside the sweep. At 2500 nm
    # the high edge can exceed the 3000 nm API cap, which returns None.
    start = max(200.0, params.centre_nm * 0.60)
    stop = min(3000.0, params.centre_nm * 1.40)
    wl = np.linspace(start, stop, 4001, dtype=np.float64)
    return _stop_band_edges(wl, g.reflectance(wl), params.centre_nm)


def _temperature_sensitivity(high, low, params):
    # A 10 K step keeps the shift well above the sweep resolution while the
    # material model remains effectively linear over that range.
    delta = 10.0
    other = params.temperature_c + delta
    if other > 200.0:
        other = params.temperature_c - delta
    if other == params.temperature_c:
        return None, None, None

    edges_now = _edges_at(high, low, params, params.temperature_c)
    edges_next = _edges_at(high, low, params, other)
    if edges_now is None or edges_next is None:
        return None, None, edges_now

    centre_now = (edges_now[0] + edges_now[1]) / 2.0
    centre_next = (edges_next[0] + edges_next[1]) / 2.0
    sensitivity = (centre_next - centre_now) / (other - params.temperature_c)
    return sensitivity, centre_now, edges_now


def run_bragg_sweep(params: BraggParams, sweep: Sweep) -> dict:
    high = _material(params.material_high)
    low  = _material(params.material_low)
    g = pc.BraggGrating(high, low, params.centre_nm, params.periods)
    g.set_temperature_c(params.temperature_c)

    wl = np.linspace(sweep.start_nm, sweep.stop_nm, sweep.n_points, dtype=np.float64)
    t0 = time.perf_counter()
    R  = g.reflectance(wl)
    compute_ms = (time.perf_counter() - t0) * 1000.0

    sensitivity, centre_nm, edges = _temperature_sensitivity(high, low, params)
    stack = g.stack_view()  # already a list of dicts
    meta = {
        "compute_ms": round(compute_ms, 3),
        "n_layers": len(stack),
        "temperature_c": params.temperature_c,
        "stop_band_centre_nm": None if centre_nm is None else round(centre_nm, 4),
        "edge_low_nm": None if edges is None else round(edges[0], 4),
        "edge_high_nm": None if edges is None else round(edges[1], 4),
        "sensitivity_nm_per_k": (
            None if sensitivity is None else round(sensitivity, 6)
        ),
    }
    return {
        "wavelengths_nm": wl.tolist(),
        "reflectance":    R.tolist(),
        "stack":          stack,
        "meta":           meta,
    }
