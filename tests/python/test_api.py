import pytest
from httpx import AsyncClient, ASGITransport
from photonics_twin_app.main import create_app
from pydantic import ValidationError
from photonics_twin_app.schemas import SimulateRequest

@pytest.fixture
def app():
    return create_app()

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
