from fastapi import APIRouter, HTTPException
from photonics_twin_app.schemas import SimulateRequest, SimulateResponse
from photonics_twin_app.sim import run_bragg_sweep

router = APIRouter(prefix="/simulate", tags=["simulate"])

@router.post("/tmm/sweep", response_model=SimulateResponse)
def simulate_tmm_sweep(req: SimulateRequest) -> SimulateResponse:
    if req.component != "bragg_grating":
        raise HTTPException(400, f"Unknown component: {req.component}")
    result = run_bragg_sweep(req.params, req.sweep)
    return SimulateResponse(**result)
