"""Independent oracle for the Born & Wolf §1.6.5 quarter-wave Bragg grating.

This script does NOT use the photonics_core C++ kernel. It computes the
reference values from the closed-form expressions in Born & Wolf so that
the test suite can compare the simulator's output against an independent
analytical reference. Run once and freeze the output into
data/validation/quarterwave_si_sio2_reference.json.
"""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

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

def main():
    # The validation sweep is wider than the user-facing default (1400-1700 nm)
    # because the Si/SiO2 stop band runs ~1219-2127 nm — the user-facing range
    # is entirely *inside* the band, so it cannot be used to locate the edges.
    centre = 1550.0
    periods = 15
    n_high = sellmeier_n(load_sellmeier("Si"),   centre)
    n_low  = sellmeier_n(load_sellmeier("SiO2"), centre)
    n_sub  = 1.0  # vacuum substrate

    # Born & Wolf §1.6.5 peak reflectance for a quarter-wave stack of N
    # high/low pairs in vacuum:  R = ((1 - q) / (1 + q))^2
    # where q = (n_low / n_high)^(2N) * (1 / n_sub)
    q = (n_low / n_high) ** (2 * periods) * (1.0 / n_sub)
    R_peak = ((1.0 - q) / (1.0 + q)) ** 2

    # Stop-band edges:
    # Δω/ω₀ = (2/π) * arcsin((n_high - n_low) / (n_high + n_low))
    # → λ_edge = λ₀ * π / (π ± 2*arcsin(...))
    a = math.asin((n_high - n_low) / (n_high + n_low))
    edge_high = centre * math.pi / (math.pi - 2.0 * a)
    edge_low  = centre * math.pi / (math.pi + 2.0 * a)

    out = {
        "description": ("Si/SiO2 quarter-wave Bragg @ 1550 nm, 15 periods, "
                        "vacuum incident & substrate. Reference: Born & Wolf §1.6.5."),
        "params": {
            "material_high": "Si", "material_low": "SiO2",
            "centre_nm": centre, "periods": periods
        },
        "sweep": {"start_nm": 800.0, "stop_nm": 2400.0, "n_points": 801},
        "reference": {
            "peak_reflectance": round(R_peak, 8),
            "peak_reflectance_tol": 1e-3,
            "peak_wavelength_nm": centre,
            "peak_wavelength_tol_nm": 0.5,
            "stop_band_edge_low_nm": round(edge_low, 4),
            "stop_band_edge_high_nm": round(edge_high, 4),
            "stop_band_edge_tol_nm": 10.0
        },
        "n_high_at_centre": round(n_high, 6),
        "n_low_at_centre":  round(n_low, 6)
    }

    out_path = ROOT / "data" / "validation" / "quarterwave_si_sio2_reference.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as fh:
        json.dump(out, fh, indent=2)
    print(f"Wrote {out_path}")

if __name__ == "__main__":
    main()
