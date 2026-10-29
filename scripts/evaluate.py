"""Reproduce the v0.1 research outputs under evaluation/outputs.

Run from the repo root after installing the package:

    .venv\\Scripts\\python.exe scripts\\evaluate.py

The script uses the installed C++ TMM kernel, not a Python re-implementation.
Its validation sections assert agreement with the independent Born & Wolf
fixtures before writing anything, so a broken build fails instead of producing
misleading research artifacts.
"""
import argparse
import csv
import json
import platform
import statistics
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from photonics_twin_app.schemas import BraggParams, Sweep
from photonics_twin_app.sim import run_bragg_sweep, run_tolerance

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evaluation" / "outputs"
REFERENCE = ROOT / "data" / "validation" / "quarterwave_si_sio2_reference.json"
MATRIX = ROOT / "data" / "validation" / "quarterwave_matrix.json"
LEVEL = 0.5


def run_sweep(start_nm, stop_nm, n_points, centre_nm=1550.0, periods=15,
              temperature_c=20.0, strain_microstrain=0.0):
    return run_bragg_sweep(
        BraggParams(material_high="Si", material_low="SiO2",
                    centre_nm=centre_nm, periods=periods,
                    temperature_c=temperature_c,
                    strain_microstrain=strain_microstrain),
        Sweep(start_nm=start_nm, stop_nm=stop_nm, n_points=n_points),
    )


def stop_band_edges(wavelengths, reflectance, centre_nm=1550.0, level=LEVEL):
    """Linear-interpolated crossings of the R>=0.5 region containing the design wavelength."""
    wl = np.asarray(wavelengths, dtype=float)
    R = np.asarray(reflectance, dtype=float)
    # Walk outward from the design wavelength, not the global max: a flat-topped
    # band makes argmax float-noise, and low-period stacks merge sidelobes into
    # the main high-reflectance region.
    start = int(np.argmin(np.abs(wl - centre_nm)))
    i = start
    while i > 0 and R[i] >= level:
        i -= 1
    j = start
    while j < len(R) - 1 and R[j] >= level:
        j += 1
    if not (R[i] < level < R[i + 1] and R[j] < level < R[j - 1]):
        raise RuntimeError("R>=0.5 region does not cross inside the sweep")

    def crossing(a, b):
        return float(wl[a] + (level - R[a]) * (wl[b] - wl[a]) / (R[b] - R[a]))

    return crossing(i, i + 1), crossing(j, j - 1)


def validation_report():
    fixture = json.loads(REFERENCE.read_text())
    params, sweep, ref = fixture["params"], fixture["sweep"], fixture["reference"]
    out = run_sweep(sweep["start_nm"], sweep["stop_nm"], sweep["n_points"],
                    params["centre_nm"], params["periods"])
    wl = np.asarray(out["wavelengths_nm"])
    R = np.asarray(out["reflectance"])
    centre_idx = int(np.argmin(np.abs(wl - ref["peak_wavelength_nm"])))
    edge_low, edge_high = stop_band_edges(wl, R)

    metrics = {
        "peak_reflectance_sim": float(R[centre_idx]),
        "peak_reflectance_reference": ref["peak_reflectance"],
        "peak_reflectance_abs_error": abs(float(R[centre_idx]) - ref["peak_reflectance"]),
        "peak_reflectance_tol": ref["peak_reflectance_tol"],
        "stop_band_edge_low_sim_nm": edge_low,
        "stop_band_edge_low_reference_nm": ref["stop_band_edge_low_nm"],
        "stop_band_edge_low_abs_error_nm": abs(edge_low - ref["stop_band_edge_low_nm"]),
        "stop_band_edge_high_sim_nm": edge_high,
        "stop_band_edge_high_reference_nm": ref["stop_band_edge_high_nm"],
        "stop_band_edge_high_abs_error_nm": abs(edge_high - ref["stop_band_edge_high_nm"]),
        "stop_band_edge_tol_nm": ref["stop_band_edge_tol_nm"],
    }
    within = (
        metrics["peak_reflectance_abs_error"] <= metrics["peak_reflectance_tol"]
        and metrics["stop_band_edge_low_abs_error_nm"] <= metrics["stop_band_edge_tol_nm"]
        and metrics["stop_band_edge_high_abs_error_nm"] <= metrics["stop_band_edge_tol_nm"]
    )
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "simulator": "photonics_core C++ TMM",
        "reference": "Born & Wolf 1.6.5 closed form",
        "params": params,
        "sweep": sweep,
        "metrics": metrics,
        "within_tolerance": within,
    }
    if not within:
        raise RuntimeError(f"simulator is outside the validation tolerance: {metrics}")
    return report


def validation_matrix():
    matrix = json.loads(MATRIX.read_text())
    rows = []
    for case in matrix["cases"]:
        params = case["params"]
        sweep = case["sweep"]
        reference = case["reference"]
        out = run_sweep(sweep["start_nm"], sweep["stop_nm"], sweep["n_points"],
                        params["centre_nm"], params["periods"])
        wl = np.asarray(out["wavelengths_nm"])
        R = np.asarray(out["reflectance"])
        index = int(np.argmin(np.abs(wl - params["centre_nm"])))
        simulated = float(R[index])
        error = abs(simulated - reference["peak_reflectance"])
        if error > reference["tolerance"]:
            raise RuntimeError(
                f"validation matrix case {params} error {error:.2e} "
                f"exceeds {reference['tolerance']:.0e}"
            )
        rows.append({
            "centre_nm": params["centre_nm"],
            "periods": params["periods"],
            "peak_reflectance_sim": simulated,
            "peak_reflectance_reference": reference["peak_reflectance"],
            "abs_error": error,
            "tolerance": reference["tolerance"],
        })
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "simulator": "photonics_core C++ TMM",
        "reference": "Born & Wolf 1.6.5 closed form",
        "cases": rows,
        "max_abs_error": max(row["abs_error"] for row in rows),
        "within_tolerance": True,
    }


def parameter_study():
    rows = []
    for periods in range(2, 17):
        # Wide sweep: low-period stacks have high sidelobes that merge with the
        # main R>=0.5 region out to ~2.7 um.
        out = run_sweep(400.0, 3000.0, 4001, periods=periods)
        wl = np.asarray(out["wavelengths_nm"])
        R = np.asarray(out["reflectance"])
        centre_idx = int(np.argmin(np.abs(wl - 1550.0)))
        edge_low, edge_high = stop_band_edges(wl, R)
        rows.append({
            "periods": periods,
            "layers": 2 * periods,
            "peak_reflectance": round(float(R[centre_idx]), 8),
            "high_reflectance_width_nm": round(edge_high - edge_low, 3),
            "edge_low_nm": round(edge_low, 3),
            "edge_high_nm": round(edge_high, 3),
            "compute_ms": out["meta"]["compute_ms"],
        })
    return rows


def temperature_study():
    rows = []
    for periods in (4, 8, 12, 15, 16):
        centres = {}
        for temperature_c in (20.0, 80.0):
            out = run_sweep(800.0, 2400.0, 4001, 1550.0, periods, temperature_c)
            wl = np.asarray(out["wavelengths_nm"])
            R = np.asarray(out["reflectance"])
            edge_low, edge_high = stop_band_edges(wl, R, centre_nm=1550.0)
            centres[temperature_c] = (edge_low + edge_high) / 2.0
        shift = centres[80.0] - centres[20.0]
        if shift <= 0.0:
            raise RuntimeError(f"temperature did not redshift the stop band at {periods} periods")
        rows.append({
            "periods": periods,
            "layers": 2 * periods,
            "centre_20c_nm": round(centres[20.0], 3),
            "centre_80c_nm": round(centres[80.0], 3),
            "shift_nm": round(shift, 3),
            "sensitivity_nm_per_k": round(shift / 60.0, 5),
        })
    return rows


def strain_study():
    rows = []
    for periods in (4, 8, 12, 15, 16):
        centres = {}
        for strain_microstrain in (0.0, 1000.0):
            out = run_sweep(800.0, 2400.0, 4001, 1550.0, periods,
                            strain_microstrain=strain_microstrain)
            wl = np.asarray(out["wavelengths_nm"])
            R = np.asarray(out["reflectance"])
            edge_low, edge_high = stop_band_edges(wl, R, centre_nm=1550.0)
            centres[strain_microstrain] = (edge_low + edge_high) / 2.0
        shift = centres[1000.0] - centres[0.0]
        if shift <= 0.0:
            raise RuntimeError(f"strain did not redshift the stop band at {periods} periods")
        rows.append({
            "periods": periods,
            "layers": 2 * periods,
            "centre_0ue_nm": round(centres[0.0], 3),
            "centre_1000ue_nm": round(centres[1000.0], 3),
            "shift_nm": round(shift, 3),
            # nm per microstrain * 1000 pm/nm == shift in pm/microstrain.
            "sensitivity_pm_per_microstrain": round(shift, 4),
        })
    return rows


def tolerance_study():
    rows = []
    params = BraggParams(material_high="Si", material_low="SiO2",
                         centre_nm=1550.0, periods=15)
    sweep = Sweep(start_nm=1400.0, stop_nm=1700.0, n_points=101)
    for sigma_nm in (0.0, 2.0, 5.0, 10.0):
        out = run_tolerance(params, sweep, 100, sigma_nm, 2.0, 12345)
        stats = out["meta"]["tolerance"]
        if stats["yield"] is None:
            raise RuntimeError(f"tolerance study produced no yield at sigma {sigma_nm}")
        if sigma_nm == 0.0 and stats["yield"] != 1.0:
            raise RuntimeError("zero-thickness-error tolerance run must have yield 1.0")
        rows.append({
            "thickness_sigma_nm": sigma_nm,
            "n_samples": stats["n_samples"],
            "valid_samples": stats["valid_samples"],
            "failed_samples": stats["failed_samples"],
            "yield": stats["yield"],
            "mean_centre_nm": stats.get("mean_centre_nm"),
            "std_centre_nm": stats.get("std_centre_nm"),
        })
    return rows


def benchmark(repeats=5):
    cases = []
    for periods in (5, 10, 15, 16):
        for n_points in (101, 501, 2001):
            samples = [run_sweep(1400.0, 1700.0, n_points, periods=periods)["meta"]["compute_ms"]
                       for _ in range(repeats)]
            median_ms = statistics.median(samples)
            cases.append({
                "periods": periods,
                "layers": 2 * periods,
                "n_points": n_points,
                "repeats": repeats,
                "median_ms": round(median_ms, 4),
                "min_ms": round(min(samples), 4),
                "max_ms": round(max(samples), 4),
                "points_per_ms": round(n_points / median_ms, 1) if median_ms else None,
            })
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "note": "compute_ms measures the C++ reflectance call only; excludes JSON and material loading.",
        "cases": cases,
    }


def write_sweep_csv(path, out):
    with path.open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["wavelength_nm", "reflectance"])
        for wavelength, reflectance in zip(out["wavelengths_nm"], out["reflectance"]):
            writer.writerow([f"{wavelength:.4f}", f"{reflectance:.10f}"])


def write_parameter_csv(path, rows):
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def summary(validation, matrix, study, temperature, strain, tolerance, bench):
    m = validation["metrics"]
    low_periods = study[0]
    high_periods = study[-1]
    fastest = max(bench["cases"], key=lambda c: c["points_per_ms"])
    lines = [
        "# Photonics Twin v0.1 - evaluation summary",
        "",
        f"Generated by `scripts/evaluate.py`. Simulator: {validation['simulator']}; "
        f"reference: {validation['reference']}.",
        "",
        "## Validation against the analytic oracle",
        "",
        "| metric | simulator | reference | abs error | tolerance |",
        "|---|---:|---:|---:|---:|",
        f"| peak reflectance | {m['peak_reflectance_sim']:.6f} | "
        f"{m['peak_reflectance_reference']:.6f} | {m['peak_reflectance_abs_error']:.2e} | "
        f"{m['peak_reflectance_tol']:.0e} |",
        f"| low stop-band edge (nm) | {m['stop_band_edge_low_sim_nm']:.2f} | "
        f"{m['stop_band_edge_low_reference_nm']:.2f} | "
        f"{m['stop_band_edge_low_abs_error_nm']:.2f} | "
        f"{m['stop_band_edge_tol_nm']:.0f} |",
        f"| high stop-band edge (nm) | {m['stop_band_edge_high_sim_nm']:.2f} | "
        f"{m['stop_band_edge_high_reference_nm']:.2f} | "
        f"{m['stop_band_edge_high_abs_error_nm']:.2f} | "
        f"{m['stop_band_edge_tol_nm']:.0f} |",
        "",
        f"Within tolerance: **{validation['within_tolerance']}**.",
        "",
        "## Peak-reflectance matrix",
        "",
        f"{len(matrix['cases'])} cases across "
        f"{len({row['centre_nm'] for row in matrix['cases']})} centre wavelengths "
        f"and {len({row['periods'] for row in matrix['cases']})} period counts. "
        f"Maximum absolute error: {matrix['max_abs_error']:.2e} "
        f"(budget {matrix['cases'][0]['tolerance']:.0e}).",
        "",
        "Full matrix is in `validation_matrix.json`. Edge validation remains the "
        "single 1550 nm, 15-period fixture because the infinite-stack edge "
        "formula is not accurate for small period counts.",
        "",
        "## Period count study (400-3000 nm sweep)",
        "",
        "| periods | layers | peak reflectance | R>=0.5 width (nm) |",
        "|---:|---:|---:|---:|",
        f"| {low_periods['periods']} | {low_periods['layers']} | "
        f"{low_periods['peak_reflectance']:.6f} | {low_periods['high_reflectance_width_nm']:.1f} |",
        f"| {high_periods['periods']} | {high_periods['layers']} | "
        f"{high_periods['peak_reflectance']:.6f} | {high_periods['high_reflectance_width_nm']:.1f} |",
        "",
        "Full sweep is in `parameter_study.csv`. For low period counts the "
        "sidelobes merge with the main high-reflectance region, so the width is "
        "not the asymptotic photonic band gap.",
        "",
        "## Temperature sensitivity (20 -> 80 C)",
        "",
        "| periods | centre 20 C (nm) | centre 80 C (nm) | shift (nm) | sensitivity (nm/K) |",
        "|---:|---:|---:|---:|---:|",
        *[
            f"| {row['periods']} | {row['centre_20c_nm']:.2f} | "
            f"{row['centre_80c_nm']:.2f} | {row['shift_nm']:.2f} | "
            f"{row['sensitivity_nm_per_k']:.4f} |"
            for row in temperature
        ],
        "",
        "Full study is in `temperature_sensitivity.csv`. The model is linear "
        "around 20 C and uses typical Si/SiO2 thermo-optic and expansion "
        "coefficients; replace them with measured data for quantitative design.",
        "",        "## Strain sensitivity (0 -> 1000 microstrain)",
        "",
        "| periods | centre 0 ue (nm) | centre 1000 ue (nm) | shift (nm) | sensitivity (pm/ue) |",
        "|---:|---:|---:|---:|---:|",
        *[
            f"| {row['periods']} | {row['centre_0ue_nm']:.2f} | "
            f"{row['centre_1000ue_nm']:.2f} | {row['shift_nm']:.2f} | "
            f"{row['sensitivity_pm_per_microstrain']:.2f} |"
            for row in strain
        ],
        "",
        "Full study is in `strain_sensitivity.csv`. This is geometric strain "
        "only; photoelastic index change is not modelled yet.",
        "",        "## Fabrication tolerance (100 samples, 2 nm target)",
        "",
        "| thickness sigma (nm) | yield | valid | failed | mean centre (nm) | std (nm) |",
        "|---:|---:|---:|---:|---:|---:|",
        *[
            f"| {row['thickness_sigma_nm']:.1f} | {row['yield']:.3f} | "
            f"{row['valid_samples']} | {row['failed_samples']} | "
            f"{row['mean_centre_nm']:.2f} | {row['std_centre_nm']:.2f} |"
            for row in tolerance
        ],
        "",
        "Yield counts a sample as failed if it has no detectable stop band or if "
        "its centre moves more than 2 nm. Full study is in `tolerance_study.csv`.",
        "",
        "## Throughput",
        "",
        f"Highest measured throughput: {fastest['points_per_ms']} wavelength points/ms "
        f"({fastest['periods']} periods, {fastest['n_points']} points). "
        "Times are medians of 5 runs on the generation host; see `benchmark.json`.",
        "",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="validate only; write no artifacts")
    args = parser.parse_args()

    validation = validation_report()
    matrix = validation_matrix()
    temperature = temperature_study()
    strain = strain_study()
    tolerance = tolerance_study()

    if args.check:
        print(f"Validation within tolerance: {validation['within_tolerance']}")
        print(f"Matrix cases: {len(matrix['cases'])}, "
              f"max abs error {matrix['max_abs_error']:.2e}")
        print(f"Temperature sensitivity (15 periods): "
              f"{next(row for row in temperature if row['periods'] == 15)['sensitivity_nm_per_k']:.4f} nm/K")
        print(f"Strain sensitivity (15 periods): "
              f"{next(row for row in strain if row['periods'] == 15)['sensitivity_pm_per_microstrain']:.2f} pm/ue")
        return

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "validation_vs_analytic.json").write_text(
        json.dumps(validation, indent=2) + "\n")
    (OUT / "validation_matrix.json").write_text(
        json.dumps(matrix, indent=2) + "\n")

    study = parameter_study()
    write_parameter_csv(OUT / "parameter_study.csv", study)
    write_parameter_csv(OUT / "temperature_sensitivity.csv", temperature)
    write_parameter_csv(OUT / "strain_sensitivity.csv", strain)
    write_parameter_csv(OUT / "tolerance_study.csv", tolerance)

    bench = benchmark()
    (OUT / "benchmark.json").write_text(json.dumps(bench, indent=2) + "\n")

    default_sweep = run_sweep(1400.0, 1700.0, 501)
    write_sweep_csv(OUT / "reflectance_default_sweep.csv", default_sweep)

    (OUT / "summary.md").write_text(
        summary(validation, matrix, study, temperature, strain, tolerance, bench))
    print(f"Wrote evaluation artifacts to {OUT}")
    print(f"Validation within tolerance: {validation['within_tolerance']}")
    print(f"Matrix max abs error: {matrix['max_abs_error']:.2e}")
    print(f"High-reflectance width 2 -> 16 periods: "
          f"{study[0]['high_reflectance_width_nm']:.1f} -> "
          f"{study[-1]['high_reflectance_width_nm']:.1f} nm")


if __name__ == "__main__":
    main()
