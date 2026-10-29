from fastapi import APIRouter, HTTPException
from photonics_twin_app.schemas import (
    BatchSweepRequest, BatchSweepResponse, SimulateRequest, SimulateResponse,
    ToleranceRequest,
)
from photonics_twin_app.sim import run_bragg_sweep, run_batch_sweep, run_tolerance

router = APIRouter(prefix="/simulate", tags=["simulate"])

@router.post("/tmm/sweep", response_model=SimulateResponse)
def simulate_tmm_sweep(req: SimulateRequest) -> SimulateResponse:
    if req.component != "bragg_grating":
        raise HTTPException(400, f"Unknown component: {req.component}")
    result = run_bragg_sweep(req.params, req.sweep)
    return SimulateResponse(**result)


@router.post("/tmm/tolerance", response_model=SimulateResponse)
def simulate_tmm_tolerance(req: ToleranceRequest) -> SimulateResponse:
    if req.component != "bragg_grating":
        raise HTTPException(400, f"Unknown component: {req.component}")
    result = run_tolerance(
        req.params, req.sweep, req.n_samples,
        req.thickness_sigma_nm, req.tolerance_nm, req.seed,
    )
    return SimulateResponse(**result)

@router.post("/tmm/batch", response_model=BatchSweepResponse)
def simulate_tmm_batch(req: BatchSweepRequest) -> BatchSweepResponse:
    if req.component != "bragg_grating":
        raise HTTPException(400, f"Unknown component: {req.component}")
    results = run_batch_sweep(req.params, req.sweep)
    return BatchSweepResponse(
        results=[SimulateResponse(**result) for result in results]
    )