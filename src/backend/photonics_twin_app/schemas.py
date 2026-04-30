from pydantic import BaseModel, Field, conint, confloat

class BraggParams(BaseModel):
    material_high: str = Field(pattern="^(Si|SiO2)$")
    material_low:  str = Field(pattern="^(Si|SiO2)$")
    centre_nm:     confloat(ge=400.0, le=2500.0)
    periods:       conint(ge=2, le=16)   # 2 * 16 == MAX_LAYERS

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
