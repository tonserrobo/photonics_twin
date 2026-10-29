import pytest
from httpx import AsyncClient, ASGITransport
from photonics_twin_app.main import create_app
from photonics_twin_app import sim
from pydantic import ValidationError
from photonics_twin_app.schemas import SimulateRequest

@pytest.fixture
def app():
    return create_app()

def test_data_dir_resolves_materials():
    assert (sim.MATERIALS_DIR / "sellmeier_si.json").is_file()
    assert (sim.MATERIALS_DIR / "sellmeier_sio2.json").is_file()

@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

async def test_healthz(client):
    r = await client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}

def test_simulate_request_valid():
    req = SimulateRequest(
        component="bragg_grating",
        params={"material_high": "Si", "material_low": "SiO2",
                "centre_nm": 1550.0, "periods": 15},
        sweep={"start_nm": 1400.0, "stop_nm": 1700.0, "n_points": 501},
    )
    assert req.params.periods == 15

def test_simulate_request_rejects_unknown_material():
    with pytest.raises(ValidationError):
        SimulateRequest(
            component="bragg_grating",
            params={"material_high": "Au", "material_low": "SiO2",
                    "centre_nm": 1550.0, "periods": 15},
            sweep={"start_nm": 1400.0, "stop_nm": 1700.0, "n_points": 501},
        )

def test_simulate_request_rejects_too_many_periods():
    with pytest.raises(ValidationError):
        SimulateRequest(
            component="bragg_grating",
            params={"material_high": "Si", "material_low": "SiO2",
                    "centre_nm": 1550.0, "periods": 17},  # > MAX_LAYERS / 2
            sweep={"start_nm": 1400.0, "stop_nm": 1700.0, "n_points": 501},
        )

import numpy as np
from photonics_twin_app.sim import run_bragg_sweep
from photonics_twin_app.schemas import BraggParams, Sweep

def test_run_bragg_sweep_shape():
    params = BraggParams(material_high="Si", material_low="SiO2",
                         centre_nm=1550.0, periods=15)
    sweep = Sweep(start_nm=1400.0, stop_nm=1700.0, n_points=501)
    out = run_bragg_sweep(params, sweep)
    assert len(out["wavelengths_nm"]) == 501
    assert len(out["reflectance"]) == 501
    assert len(out["stack"]) == 30
    assert "compute_ms" in out["meta"]
    assert out["meta"]["n_layers"] == 30

async def test_simulate_tmm_sweep_smoke(client):
    body = {
        "component": "bragg_grating",
        "params": {"material_high": "Si", "material_low": "SiO2",
                   "centre_nm": 1550.0, "periods": 15},
        "sweep":  {"start_nm": 1400.0, "stop_nm": 1700.0, "n_points": 501},
    }
    r = await client.post("/simulate/tmm/sweep", json=body)
    assert r.status_code == 200
    data = r.json()
    assert len(data["wavelengths_nm"]) == 501
    assert len(data["reflectance"])    == 501
    assert len(data["stack"])          == 30
    assert data["meta"]["n_layers"]    == 30

async def test_simulate_validation_error(client):
    body = {
        "component": "bragg_grating",
        "params": {"material_high": "Au", "material_low": "SiO2",
                   "centre_nm": 1550.0, "periods": 15},
        "sweep":  {"start_nm": 1400.0, "stop_nm": 1700.0, "n_points": 501},
    }
    r = await client.post("/simulate/tmm/sweep", json=body)
    assert r.status_code == 422
    assert "material_high" in r.text

async def test_mock_slurm_echo(client):
    payload = {"job_kind": "bragg_sweep", "params": {"centre_nm": 1550.0}}
    r = await client.post("/mock/slurm/submit", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "accepted"
    assert data["job_id"].startswith("mock-")
    assert data["echo"] == payload
    assert "received_at" in data

async def test_temperature_sensitivity(client):
    def body(temperature_c):
        return {
            "component": "bragg_grating",
            "params": {"material_high": "Si", "material_low": "SiO2",
                       "centre_nm": 1550.0, "periods": 15,
                       "temperature_c": temperature_c},
            "sweep":  {"start_nm": 1400.0, "stop_nm": 1700.0, "n_points": 101},
        }

    r20 = await client.post("/simulate/tmm/sweep", json=body(20.0))
    r60 = await client.post("/simulate/tmm/sweep", json=body(60.0))
    assert r20.status_code == 200
    assert r60.status_code == 200

    meta20 = r20.json()["meta"]
    meta60 = r60.json()["meta"]
    assert meta20["temperature_c"] == 20.0
    assert meta60["temperature_c"] == 60.0
    assert meta60["stop_band_centre_nm"] > meta20["stop_band_centre_nm"] + 1.0
    assert 0.02 < meta60["sensitivity_nm_per_k"] < 0.2

async def test_temperature_out_of_range(client):
    body = {
        "component": "bragg_grating",
        "params": {"material_high": "Si", "material_low": "SiO2",
                   "centre_nm": 1550.0, "periods": 15,
                   "temperature_c": 250.0},
        "sweep":  {"start_nm": 1400.0, "stop_nm": 1700.0, "n_points": 101},
    }
    r = await client.post("/simulate/tmm/sweep", json=body)
    assert r.status_code == 422
    assert "temperature_c" in r.text
async def test_strain_sensitivity(client):
    def body(strain_microstrain):
        return {
            "component": "bragg_grating",
            "params": {"material_high": "Si", "material_low": "SiO2",
                       "centre_nm": 1550.0, "periods": 15,
                       "strain_microstrain": strain_microstrain},
            "sweep":  {"start_nm": 1400.0, "stop_nm": 1700.0, "n_points": 101},
        }

    r0 = await client.post("/simulate/tmm/sweep", json=body(0.0))
    r1000 = await client.post("/simulate/tmm/sweep", json=body(1000.0))
    assert r0.status_code == 200
    assert r1000.status_code == 200

    meta0 = r0.json()["meta"]
    meta1000 = r1000.json()["meta"]
    assert meta0["strain_microstrain"] == 0.0
    assert meta1000["strain_microstrain"] == 1000.0
    assert meta1000["stop_band_centre_nm"] > meta0["stop_band_centre_nm"] + 1.0
    assert 1.0 < meta1000["strain_sensitivity_pm_per_microstrain"] < 3.0

async def test_strain_out_of_range(client):
    body = {
        "component": "bragg_grating",
        "params": {"material_high": "Si", "material_low": "SiO2",
                   "centre_nm": 1550.0, "periods": 15,
                   "strain_microstrain": 6000.0},
        "sweep":  {"start_nm": 1400.0, "stop_nm": 1700.0, "n_points": 101},
    }
    r = await client.post("/simulate/tmm/sweep", json=body)
    assert r.status_code == 422
    assert "strain_microstrain" in r.text

from fastapi.testclient import TestClient

def test_ws_sim_recompute(app):
    sync_client = TestClient(app)
    with sync_client.websocket_connect("/ws/sim?component=bragg_grating") as ws:
        ws.send_json({
            "type": "simulate",
            "params": {"material_high": "Si", "material_low": "SiO2",
                       "centre_nm": 1550.0, "periods": 15},
            "sweep":  {"start_nm": 1400.0, "stop_nm": 1700.0, "n_points": 101},
        })
        msg = ws.receive_json()
        assert msg["type"] == "result"
        assert len(msg["wavelengths_nm"]) == 101
        assert len(msg["reflectance"])    == 101

def test_ws_sim_validation_error(app):
    sync_client = TestClient(app)
    with sync_client.websocket_connect("/ws/sim?component=bragg_grating") as ws:
        ws.send_json({
            "type": "simulate",
            "params": {"material_high": "Au", "material_low": "SiO2",
                       "centre_nm": 1550.0, "periods": 15},
            "sweep":  {"start_nm": 1400.0, "stop_nm": 1700.0, "n_points": 101},
        })
        msg = ws.receive_json()
        assert msg["type"] == "error"
        assert "code" in msg and "message" in msg

async def test_tolerance_zero_sigma_is_deterministic(client):
    body = {
        "component": "bragg_grating",
        "params": {"material_high": "Si", "material_low": "SiO2",
                   "centre_nm": 1550.0, "periods": 15},
        "sweep": {"start_nm": 1400.0, "stop_nm": 1700.0, "n_points": 101},
        "n_samples": 20,
        "thickness_sigma_nm": 0.0,
        "tolerance_nm": 2.0,
        "seed": 7,
    }
    r = await client.post("/simulate/tmm/tolerance", json=body)
    assert r.status_code == 200
    stats = r.json()["meta"]["tolerance"]
    assert stats["valid_samples"] == 20
    assert stats["yield"] == 1.0
    assert stats["std_centre_nm"] == 0.0

async def test_tolerance_smoke(client):
    body = {
        "component": "bragg_grating",
        "params": {"material_high": "Si", "material_low": "SiO2",
                   "centre_nm": 1550.0, "periods": 15},
        "sweep": {"start_nm": 1400.0, "stop_nm": 1700.0, "n_points": 101},
        "n_samples": 30,
        "thickness_sigma_nm": 5.0,
        "tolerance_nm": 2.0,
        "seed": 7,
    }
    r = await client.post("/simulate/tmm/tolerance", json=body)
    assert r.status_code == 200
    stats = r.json()["meta"]["tolerance"]
    assert stats["valid_samples"] + stats["failed_samples"] == 30
    assert stats["valid_samples"] >= 20
    assert 0.0 <= stats["yield"] <= 1.0
    assert stats["yield"] <= stats["valid_samples"] / 30
    assert stats["p05_centre_nm"] <= stats["p95_centre_nm"]
    assert abs(stats["mean_centre_nm"] - stats["nominal_centre_nm"]) < 20.0

async def test_tolerance_rejects_too_many_samples(client):
    body = {
        "component": "bragg_grating",
        "params": {"material_high": "Si", "material_low": "SiO2",
                   "centre_nm": 1550.0, "periods": 15},
        "sweep": {"start_nm": 1400.0, "stop_nm": 1700.0, "n_points": 101},
        "n_samples": 500,
    }
    r = await client.post("/simulate/tmm/tolerance", json=body)
    assert r.status_code == 422
    assert "n_samples" in r.text
async def test_batch_sweep(client):
    body = {
        "component": "bragg_grating",
        "params": [
            {"material_high": "Si", "material_low": "SiO2",
             "centre_nm": 1550.0, "periods": 10},
            {"material_high": "Si", "material_low": "SiO2",
             "centre_nm": 1550.0, "periods": 15},
        ],
        "sweep": {"start_nm": 1400.0, "stop_nm": 1700.0, "n_points": 101},
    }
    r = await client.post("/simulate/tmm/batch", json=body)
    assert r.status_code == 200
    results = r.json()["results"]
    assert len(results) == 2
    assert results[0]["meta"]["n_layers"] == 20
    assert results[1]["meta"]["n_layers"] == 30
    assert len(results[0]["reflectance"]) == 101

async def test_batch_rejects_empty(client):
    body = {
        "component": "bragg_grating",
        "params": [],
        "sweep": {"start_nm": 1400.0, "stop_nm": 1700.0, "n_points": 101},
    }
    r = await client.post("/simulate/tmm/batch", json=body)
    assert r.status_code == 422
    assert "params" in r.text

async def test_measurement_resolution(client):
    body = {
        "component": "bragg_grating",
        "params": {"material_high": "Si", "material_low": "SiO2",
                   "centre_nm": 1550.0, "periods": 15,
                   "wavelength_noise_nm": 0.01},
        "sweep": {"start_nm": 1400.0, "stop_nm": 1700.0, "n_points": 101},
    }
    r = await client.post("/simulate/tmm/sweep", json=body)
    assert r.status_code == 200
    meta = r.json()["meta"]
    assert 0.1 < meta["temperature_resolution_k"] < 0.3
    assert 4.0 < meta["strain_resolution_microstrain"] < 9.0

async def test_zero_noise_gives_zero_resolution(client):
    body = {
        "component": "bragg_grating",
        "params": {"material_high": "Si", "material_low": "SiO2",
                   "centre_nm": 1550.0, "periods": 15,
                   "wavelength_noise_nm": 0.0},
        "sweep": {"start_nm": 1400.0, "stop_nm": 1700.0, "n_points": 101},
    }
    r = await client.post("/simulate/tmm/sweep", json=body)
    assert r.status_code == 200
    meta = r.json()["meta"]
    assert meta["temperature_resolution_k"] == 0.0
    assert meta["strain_resolution_microstrain"] == 0.0