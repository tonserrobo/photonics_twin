from pydantic import BaseModel, Field, conint, confloat

class BraggParams(BaseModel):
    material_high: str = Field(pattern="^(Si|SiO2)$")
    material_low:  str = Field(pattern="^(Si|SiO2)$")
    centre_nm:     confloat(ge=400.0, le=2500.0)
    periods:       conint(ge=2, le=16)   # 2 * 16 == MAX_LAYERS
    temperature_c: confloat(ge=-40.0, le=200.0) = 20.0
    strain_microstrain: confloat(ge=-5000.0, le=5000.0) = 0.0
    wavelength_noise_nm: confloat(ge=0.0, le=1.0) = 0.01

class Sweep(BaseModel):
    start_nm: confloat(ge=200.0, le=3000.0)
    stop_nm:  confloat(ge=200.0, le=3000.0)
    n_points: conint(ge=11, le=4001)

class SimulateRequest(BaseModel):
    component: str
    params: BraggParams
    sweep:  Sweep

class LayerOut(BaseModel):
    index: int
    material: str
    thickness_nm: float
    n_at_centre: float

class SimulateResponse(BaseModel):
    wavelengths_nm: list[float]
    reflectance:    list[float]
    stack: list[LayerOut]
    meta:  dict

class ToleranceRequest(BaseModel):
    component: str
    params: BraggParams
    sweep: Sweep
    n_samples: conint(ge=10, le=200) = 50
    thickness_sigma_nm: confloat(ge=0.0, le=50.0) = 5.0
    tolerance_nm: confloat(ge=0.1, le=50.0) = 2.0
    seed: conint(ge=0, le=4294967295) = 12345
class BatchSweepRequest(BaseModel):
    component: str
    params: list[BraggParams] = Field(min_length=1, max_length=50)
    sweep: Sweep

class BatchSweepResponse(BaseModel):
    results: list[SimulateResponse]