from pydantic import BaseModel
from datetime import date
from typing import Optional

class MFBase(BaseModel):
    scheme_name: str
    depositor_name: Optional[str] = None
    depositor_code: Optional[str] = None
    holder: Optional[str] = None
    isin: Optional[str] = None
    units: float
    invested_amount: float
    transaction_date: Optional[date] = None
    amc_name: Optional[str] = None
    amfi_code: Optional[str] = None
    interest_rate: Optional[float] = 0.0

class MFCreate(MFBase):
    pass

class MFSchema(MFBase):
    id: int
    user_id: int
    p_buy_units: Optional[float] = 0.0
    p_sell_units: Optional[float] = 0.0

    class Config:
        from_attributes = True
