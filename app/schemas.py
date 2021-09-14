from typing import Optional
from pydantic import BaseModel

class RequestBuildModel(BaseModel):
    MTR: Optional[int] = None
    AVCI: Optional[int] = None
    ECNT: Optional[int] = None
    CIL: Optional[int] = None
    RPM_PER: Optional[int] = None
    CPWM_ENABLE: Optional[bool] = None
    SINC_ENABLE: Optional[bool] = None
    DNT: Optional[int] = None
    ALPHA: Optional[int] = None
    ED: Optional[int] = None
    PMSI: Optional[int] = None
    TPS_DUAL: Optional[bool] = None
    TPS_MIN_A: Optional[int] = None
    TPS_MIN_B: Optional[int] = None 
    TPS_MAX_A: Optional[int] = None
    TPS_CALC_A: Optional[str] = None
    TEMP_MIN: Optional[int] = None
    TEMP_MAX: Optional[int] = None
