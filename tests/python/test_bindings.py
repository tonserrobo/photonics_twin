import pytest
import photonics_core as pc
import numpy as np

def test_material_n_at_633nm(sio2_coeffs):
    m = pc.Material("SiO2", pc.SellmeierCoeffs(*sio2_coeffs))
    assert abs(m.n(633.0) - 1.4570) < 1e-4

def test_material_name(si_coeffs):
    m = pc.Material("Si", pc.SellmeierCoeffs(*si_coeffs))
    assert m.name == "Si"

def test_material_temperature_shift(si_coeffs):
    m = pc.Material("Si", pc.SellmeierCoeffs(*si_coeffs),
                    pc.ThermalCoeffs(1.86e-4, 2.6e-6))
    assert abs(m.n(1550.0, 20.0) - m.n(1550.0)) < 1e-12
    assert m.n(1550.0, 60.0) > m.n(1550.0, 20.0)
    assert abs(m.dn_dT - 1.86e-4) < 1e-12
    assert abs(m.cte - 2.6e-6) < 1e-12

def test_bragg_reflectance_roundtrip(si_coeffs, sio2_coeffs):
    si  = pc.Material("Si",   pc.SellmeierCoeffs(*si_coeffs))
    sio = pc.Material("SiO2", pc.SellmeierCoeffs(*sio2_coeffs))
    g = pc.BraggGrating(si, sio, 1550.0, 15)

    wl = np.linspace(1400.0, 1700.0, 501, dtype=np.float64)
    R = g.reflectance(wl)
    assert R.shape == (501,)
    assert R.dtype == np.float64
    assert R.flags["C_CONTIGUOUS"]

    peak = float(wl[int(np.argmax(R))])
    # The 1400-1700 sweep is entirely inside the Si/SiO2 stop band; argmax
    # is dominated by floating-point noise, so we only assert it lands
    # inside a generous window around the design wavelength.
    assert abs(peak - 1550.0) < 50.0
    assert R.max() > 0.99
    assert R.min() > 0.99   # entire sweep inside the stop band

def test_bragg_stack_layer_count(si_coeffs, sio2_coeffs):
    si  = pc.Material("Si",   pc.SellmeierCoeffs(*si_coeffs))
    sio = pc.Material("SiO2", pc.SellmeierCoeffs(*sio2_coeffs))
    g = pc.BraggGrating(si, sio, 1550.0, 15)
    layers = g.stack_view()
    assert len(layers) == 30
    assert layers[0]["material"] == "Si"
    assert layers[1]["material"] == "SiO2"
    assert layers[0]["thickness_nm"] > 0
    assert "n_at_centre" in layers[0]

def _low_stop_band_edge(wavelengths, reflectance):
    for i in range(1, len(reflectance)):
        if reflectance[i - 1] < 0.5 <= reflectance[i]:
            return float(
                wavelengths[i - 1]
                + (0.5 - reflectance[i - 1]) * (wavelengths[i] - wavelengths[i - 1])
                / (reflectance[i] - reflectance[i - 1])
            )
    raise AssertionError("no 0.5 crossing found")

def test_bragg_temperature_redshift(si_coeffs, sio2_coeffs):
    si = pc.Material("Si", pc.SellmeierCoeffs(*si_coeffs),
                     pc.ThermalCoeffs(1.86e-4, 2.6e-6))
    sio = pc.Material("SiO2", pc.SellmeierCoeffs(*sio2_coeffs),
                      pc.ThermalCoeffs(1.0e-5, 5.5e-7))
    g = pc.BraggGrating(si, sio, 1550.0, 15)

    wl = np.linspace(1150.0, 1300.0, 1501, dtype=np.float64)
    edge_20 = _low_stop_band_edge(wl, g.reflectance(wl))
    g.set_temperature_c(80.0)
    edge_80 = _low_stop_band_edge(wl, g.reflectance(wl))

    assert edge_80 > edge_20 + 1.0
    assert edge_80 < edge_20 + 10.0

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

def test_reference_fixture(si_coeffs, sio2_coeffs):
    fixture_path = REPO_ROOT / "data" / "validation" / "quarterwave_si_sio2_reference.json"
    fixture = json.loads(fixture_path.read_text())
    p = fixture["params"]; sw = fixture["sweep"]; ref = fixture["reference"]

    si  = pc.Material("Si",   pc.SellmeierCoeffs(*si_coeffs))
    sio = pc.Material("SiO2", pc.SellmeierCoeffs(*sio2_coeffs))
    g = pc.BraggGrating(si, sio, p["centre_nm"], p["periods"])

    wl = np.linspace(sw["start_nm"], sw["stop_nm"], sw["n_points"], dtype=np.float64)
    R = g.reflectance(wl)

    # Peak reflectance: assert R at the centre wavelength is near the analytical
    # value (not argmax, which is unreliable inside a flat-top stop band).
    centre_idx = int(np.round((ref["peak_wavelength_nm"] - sw["start_nm"])
                              / (sw["stop_nm"] - sw["start_nm"]) * (sw["n_points"] - 1)))
    assert abs(float(wl[centre_idx]) - ref["peak_wavelength_nm"]) < 1e-6, \
        "centre wavelength must land exactly on the sweep grid"
    assert abs(float(R[centre_idx]) - ref["peak_reflectance"]) < ref["peak_reflectance_tol"]

    # Stop-band edges: walk outward from the global peak and find the first
    # crossing through R = 0.5 in each direction. This isolates the main
    # stop band from sidelobes (high-index-contrast stacks have sidelobes
    # that also exceed 0.5 but are disconnected from the central peak).
    peak_idx = int(np.argmax(R))
    i = peak_idx
    while i > 0 and R[i] > 0.5:
        i -= 1
    assert i > 0, "main stop band runs off the low end of the sweep"
    edge_low_meas = float(wl[i + 1])

    j = peak_idx
    while j < len(R) - 1 and R[j] > 0.5:
        j += 1
    assert j < len(R) - 1, "main stop band runs off the high end of the sweep"
    edge_high_meas = float(wl[j - 1])

    assert abs(edge_low_meas  - ref["stop_band_edge_low_nm"])  < ref["stop_band_edge_tol_nm"], \
        f"low edge: simulator {edge_low_meas:.2f} vs Born&Wolf {ref['stop_band_edge_low_nm']:.2f}"
    assert abs(edge_high_meas - ref["stop_band_edge_high_nm"]) < ref["stop_band_edge_tol_nm"], \
        f"high edge: simulator {edge_high_meas:.2f} vs Born&Wolf {ref['stop_band_edge_high_nm']:.2f}"

def test_bragg_strain_redshift(si_coeffs, sio2_coeffs):
    si = pc.Material("Si", pc.SellmeierCoeffs(*si_coeffs),
                     pc.ThermalCoeffs(1.86e-4, 2.6e-6))
    sio = pc.Material("SiO2", pc.SellmeierCoeffs(*sio2_coeffs),
                      pc.ThermalCoeffs(1.0e-5, 5.5e-7))
    g = pc.BraggGrating(si, sio, 1550.0, 15)

    wl = np.linspace(1150.0, 1300.0, 1501, dtype=np.float64)
    edge_0 = _low_stop_band_edge(wl, g.reflectance(wl))
    g.set_strain_microstrain(1000.0)
    edge_1000 = _low_stop_band_edge(wl, g.reflectance(wl))

    assert edge_1000 > edge_0 + 0.5
    assert edge_1000 < edge_0 + 3.0
def test_bragg_thickness_scales_change_spectrum(si_coeffs, sio2_coeffs):
    si = pc.Material("Si", pc.SellmeierCoeffs(*si_coeffs))
    sio = pc.Material("SiO2", pc.SellmeierCoeffs(*sio2_coeffs))
    g = pc.BraggGrating(si, sio, 1550.0, 2)

    wl = np.linspace(1400.0, 1700.0, 501, dtype=np.float64)
    R0 = g.reflectance(wl)
    g.set_thickness_scales([1.05, 0.95, 1.05, 0.95])
    R1 = g.reflectance(wl)
    assert np.max(np.abs(R1 - R0)) > 1e-3

    g.clear_thickness_scales()
    R2 = g.reflectance(wl)
    assert np.allclose(R2, R0, atol=1e-12)

    with pytest.raises(RuntimeError, match="2 \\* periods"):
        g.set_thickness_scales([1.0, 1.0, 1.0])