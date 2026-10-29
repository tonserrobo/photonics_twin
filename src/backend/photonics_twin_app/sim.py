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


def _edges_at(high, low, params, temperature_c, strain_microstrain,
              scales=None, n_points=4001):
    g = pc.BraggGrating(high, low, params.centre_nm, params.periods)
    g.set_temperature_c(temperature_c)
    g.set_strain_microstrain(strain_microstrain)
    if scales is not None:
        g.set_thickness_scales(scales)
    # Wider than the stop band so both edges are inside the sweep. At 2500 nm
    # the high edge can exceed the 3000 nm API cap, which returns None.
    start = max(200.0, params.centre_nm * 0.60)
    stop = min(3000.0, params.centre_nm * 1.40)
    wl = np.linspace(start, stop, n_points, dtype=np.float64)
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

    edges_now = _edges_at(high, low, params, params.temperature_c,
                          params.strain_microstrain)
    edges_next = _edges_at(high, low, params, other,
                           params.strain_microstrain)
    if edges_now is None or edges_next is None:
        return None, None, edges_now

    centre_now = (edges_now[0] + edges_now[1]) / 2.0
    centre_next = (edges_next[0] + edges_next[1]) / 2.0
    sensitivity = (centre_next - centre_now) / (other - params.temperature_c)
    return sensitivity, centre_now, edges_now


def _strain_sensitivity(high, low, params, centre_now):
    # Geometric strain only: layer thickness scales with (1 + strain). A
    # 1000 microstrain step gives a ~1.7 nm shift, well above sweep resolution.
    delta = 1000.0
    other = params.strain_microstrain + delta
    if other > 5000.0:
        other = params.strain_microstrain - delta
    if other == params.strain_microstrain:
        return None

    edges_other = _edges_at(high, low, params, params.temperature_c, other)
    if edges_other is None or centre_now is None:
        return None
    centre_other = (edges_other[0] + edges_other[1]) / 2.0
    nm_per_microstrain = (centre_other - centre_now) / (other - params.strain_microstrain)
    return nm_per_microstrain * 1000.0


def run_bragg_sweep(params: BraggParams, sweep: Sweep) -> dict:
    high = _material(params.material_high)
    low  = _material(params.material_low)
    g = pc.BraggGrating(high, low, params.centre_nm, params.periods)
    g.set_temperature_c(params.temperature_c)
    g.set_strain_microstrain(params.strain_microstrain)

    wl = np.linspace(sweep.start_nm, sweep.stop_nm, sweep.n_points, dtype=np.float64)
    t0 = time.perf_counter()
    R  = g.reflectance(wl)
    compute_ms = (time.perf_counter() - t0) * 1000.0

    temperature_sensitivity, centre_nm, edges = _temperature_sensitivity(
        high, low, params)
    strain_sensitivity = _strain_sensitivity(high, low, params, centre_nm)
    noise_nm = params.wavelength_noise_nm
    temp_resolution = (
        None if not temperature_sensitivity
        else noise_nm / abs(temperature_sensitivity)
    )
    strain_resolution = (
        None if not strain_sensitivity
        else noise_nm * 1000.0 / abs(strain_sensitivity)
    )
    stack = g.stack_view()  # already a list of dicts
    meta = {
        "compute_ms": round(compute_ms, 3),
        "n_layers": len(stack),
        "temperature_c": params.temperature_c,
        "strain_microstrain": params.strain_microstrain,
        "stop_band_centre_nm": None if centre_nm is None else round(centre_nm, 4),
        "edge_low_nm": None if edges is None else round(edges[0], 4),
        "edge_high_nm": None if edges is None else round(edges[1], 4),
        "sensitivity_nm_per_k": (
            None if temperature_sensitivity is None
            else round(temperature_sensitivity, 6)
        ),
        "strain_sensitivity_pm_per_microstrain": (
            None if strain_sensitivity is None
            else round(strain_sensitivity, 4)
        ),
        "wavelength_noise_nm": noise_nm,
        "temperature_resolution_k": (
            None if temp_resolution is None else round(temp_resolution, 6)
        ),
        "strain_resolution_microstrain": (
            None if strain_resolution is None else round(strain_resolution, 4)
        ),
    }
    return {
        "wavelengths_nm": wl.tolist(),
        "reflectance":    R.tolist(),
        "stack":          stack,
        "meta":           meta,
    }


def run_batch_sweep(params_list, sweep):
    return [run_bragg_sweep(params, sweep) for params in params_list]


def run_tolerance(params, sweep, n_samples, thickness_sigma_nm,
                  tolerance_nm, seed):
    """Monte Carlo over per-layer thickness errors, seeded for reproducibility."""
    high = _material(params.material_high)
    low = _material(params.material_low)
    nominal = run_bragg_sweep(params, sweep)
    thicknesses = np.asarray(
        [layer["thickness_nm"] for layer in nominal["stack"]], dtype=float)
    nominal_centre = nominal["meta"]["stop_band_centre_nm"]

    rng = np.random.default_rng(seed)
    centres = []
    t0 = time.perf_counter()
    for _ in range(n_samples):
        if thickness_sigma_nm > 0.0:
            relative_sigma = thickness_sigma_nm / thicknesses
            scales = np.clip(1.0 + rng.normal(0.0, relative_sigma), 0.5, 1.5)
        else:
            scales = np.ones_like(thicknesses)
        edges = _edges_at(
            high, low, params, params.temperature_c, params.strain_microstrain,
            scales=scales.tolist(), n_points=2001)
        if edges is not None:
            centres.append((edges[0] + edges[1]) / 2.0)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    centres = np.asarray(centres, dtype=float)
    n_valid = int(centres.size)
    failed = n_samples - n_valid
    if nominal_centre is None or n_valid == 0:
        stats = {
            "n_samples": n_samples,
            "valid_samples": n_valid,
            "failed_samples": failed,
            "thickness_sigma_nm": thickness_sigma_nm,
            "tolerance_nm": tolerance_nm,
            "seed": seed,
            "nominal_centre_nm": nominal_centre,
            "yield": None,
            "compute_ms": round(elapsed_ms, 3),
        }
    else:
        shifts = centres - nominal_centre
        within = int(np.sum(np.abs(shifts) <= tolerance_nm))
        stats = {
            "n_samples": n_samples,
            "valid_samples": n_valid,
            "failed_samples": failed,
            "thickness_sigma_nm": thickness_sigma_nm,
            "tolerance_nm": tolerance_nm,
            "seed": seed,
            "nominal_centre_nm": round(float(nominal_centre), 4),
            "mean_centre_nm": round(float(centres.mean()), 4),
            "std_centre_nm": round(float(centres.std(ddof=1)), 4)
            if centres.size > 1 else 0.0,
            "p05_centre_nm": round(float(np.percentile(centres, 5)), 4),
            "p95_centre_nm": round(float(np.percentile(centres, 95)), 4),
            "min_centre_nm": round(float(centres.min()), 4),
            "max_centre_nm": round(float(centres.max()), 4),
            "yield": round(within / n_samples, 4),
            "yield_definition": (
                "fraction of all samples within +/- tolerance_nm of nominal; "
                "samples with no detectable stop band count as failures"
            ),
            "compute_ms": round(elapsed_ms, 3),
        }
    nominal["meta"]["tolerance"] = stats
    return nominal