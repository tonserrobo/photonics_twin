import json
from pathlib import Path

import numpy as np

from photonics_twin_app.schemas import BraggParams, Sweep
from photonics_twin_app.sim import run_bragg_sweep

REPO_ROOT = Path(__file__).resolve().parents[2]
MATRIX_PATH = REPO_ROOT / "data" / "validation" / "quarterwave_matrix.json"


def test_validation_matrix_peak_reflectance():
    matrix = json.loads(MATRIX_PATH.read_text())
    cases = matrix["cases"]
    assert cases, "validation matrix must contain cases"

    for case in cases:
        params = case["params"]
        sweep = case["sweep"]
        reference = case["reference"]

        result = run_bragg_sweep(BraggParams(**params), Sweep(**sweep))
        wavelengths = np.asarray(result["wavelengths_nm"])
        reflectance = np.asarray(result["reflectance"])
        index = int(np.argmin(np.abs(wavelengths - params["centre_nm"])))

        assert abs(float(wavelengths[index]) - params["centre_nm"]) < 1e-6, \
            f"{params}: centre must land on the sweep grid"
        error = abs(float(reflectance[index]) - reference["peak_reflectance"])
        assert error <= reference["tolerance"], \
            f"{params}: peak reflectance error {error:.2e} > {reference['tolerance']:.0e}"
