"""Independent oracle for the Born & Wolf 1.6.5 quarter-wave Bragg grating.

This script does NOT use the photonics_core C++ kernel. It computes reference
values from the closed-form expressions in Born & Wolf so the test suite can
compare the simulator against an independent analytical reference.

It writes two files:

- data/validation/quarterwave_si_sio2_reference.json - the canonical 1550 nm,
  15-period fixture with peak reflectance and stop-band edges.
- data/validation/quarterwave_matrix.json - peak reflectance across centre
  wavelengths and period counts, used by tests and the evaluation pack.

Run once and freeze the output; the test harness does not call this script.
"""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VALIDATION_DIR = ROOT / "data" / "validation"

CENTRES_NM = (1310.0, 1550.0, 2000.0)
PERIODS = (4, 8, 12, 15, 16)
MATRIX_TOLERANCE = 1e-6


def load_sellmeier(name):
    with open(ROOT / "data" / "materials" / f"sellmeier_{name.lower()}.json") as fh:
        return json.load(fh)["coeffs"]


def sellmeier_n(coeffs, wavelength_nm):
    lam = wavelength_nm / 1000.0
    l2 = lam * lam
    s = (coeffs["B1"] * l2 / (l2 - coeffs["C1"]) +
         coeffs["B2"] * l2 / (l2 - coeffs["C2"]) +
         coeffs["B3"] * l2 / (l2 - coeffs["C3"]))
    return math.sqrt(1.0 + s)


def peak_reference(centre_nm, periods):
    n_high = sellmeier_n(load_sellmeier("Si"), centre_nm)
    n_low = sellmeier_n(load_sellmeier("SiO2"), centre_nm)
    q = (n_low / n_high) ** (2 * periods)
    peak = ((1.0 - q) / (1.0 + q)) ** 2
    return n_high, n_low, peak


def write_single_fixture():
    # The validation sweep is wider than the user-facing default (1400-1700 nm)
    # because the Si/SiO2 stop band runs ~1219-2127 nm - the user-facing range
    # is entirely inside the band, so it cannot be used to locate the edges.
    centre = 1550.0
    periods = 15
    n_high, n_low, R_peak = peak_reference(centre, periods)

    # Infinite-stack stop-band edges. The finite 15-period stack converges
    # close to these, which is why the fixture uses this case.
    a = math.asin((n_high - n_low) / (n_high + n_low))
    edge_high = centre * math.pi / (math.pi - 2.0 * a)
    edge_low = centre * math.pi / (math.pi + 2.0 * a)

    out = {
        "description": ("Si/SiO2 quarter-wave Bragg @ 1550 nm, 15 periods, "
                        "vacuum incident & substrate. Reference: Born & Wolf 1.6.5."),
        "params": {
            "material_high": "Si", "material_low": "SiO2",
            "centre_nm": centre, "periods": periods,
        },
        "sweep": {"start_nm": 800.0, "stop_nm": 2400.0, "n_points": 801},
        "reference": {
            "peak_reflectance": round(R_peak, 8),
            "peak_reflectance_tol": 1e-3,
            "peak_wavelength_nm": centre,
            "peak_wavelength_tol_nm": 0.5,
            "stop_band_edge_low_nm": round(edge_low, 4),
            "stop_band_edge_high_nm": round(edge_high, 4),
            "stop_band_edge_tol_nm": 10.0,
        },
        "n_high_at_centre": round(n_high, 6),
        "n_low_at_centre": round(n_low, 6),
    }

    path = VALIDATION_DIR / "quarterwave_si_sio2_reference.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2) + "\n")
    print(f"Wrote {path}")


def write_matrix():
    cases = []
    for centre in CENTRES_NM:
        for periods in PERIODS:
            n_high, n_low, peak = peak_reference(centre, periods)
            cases.append({
                "params": {
                    "material_high": "Si", "material_low": "SiO2",
                    "centre_nm": centre, "periods": periods,
                },
                # 1 nm step with the design centre exactly on the grid.
                "sweep": {
                    "start_nm": centre - 200.0,
                    "stop_nm": centre + 200.0,
                    "n_points": 401,
                },
                "reference": {
                    "peak_reflectance": round(peak, 12),
                    "tolerance": MATRIX_TOLERANCE,
                    "n_high_at_centre": round(n_high, 6),
                    "n_low_at_centre": round(n_low, 6),
                },
            })

    out = {
        "description": ("Si/SiO2 quarter-wave peak reflectance matrix. "
                        "Reference: Born & Wolf 1.6.5. Edge validation remains "
                        "in quarterwave_si_sio2_reference.json because the "
                        "infinite-stack edge formula is not accurate for small "
                        "period counts."),
        "material_pair": ["Si", "SiO2"],
        "tolerance": MATRIX_TOLERANCE,
        "cases": cases,
    }

    path = VALIDATION_DIR / "quarterwave_matrix.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2) + "\n")
    print(f"Wrote {path}")


def main():
    write_single_fixture()
    write_matrix()


if __name__ == "__main__":
    main()
