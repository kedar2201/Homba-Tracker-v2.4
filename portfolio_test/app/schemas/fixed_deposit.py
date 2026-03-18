from pydantic import BaseModel
from datetime import date
from typing import Optional
from enum import Enum as PyEnum

# Use Enums matching DB
class CompoundingFrequency(str, PyEnum):
    MONTHLY = "Monthly"
    QUARTERLY = "Quarterly"
    HALF_YEARLY = "Half-Yearly"
    YEARLY = "Yearly"
    MATURITY = "On Maturity"

class PayoutType(str, PyEnum):
    CUMULATIVE = "Cumulative"
    MONTHLY_PAYOUT = "Monthly Payout"
    QUARTERLY_PAYOUT = "Quarterly Payout"
    HALF_YEARLY_PAYOUT = "Half-Yearly Payout"
    ANNUAL_PAYOUT = "Annual Payout"

class FDBase(BaseModel):
    bank_name: str
    depositor_name: Optional[str] = None
    depositor_code: Optional[str] = None
    fd_code: str
    principal: float
    interest_rate: float
    start_date: Optional[date] = None
    maturity_date: Optional[date] = None
    compounding_frequency: CompoundingFrequency = CompoundingFrequency.YEARLY
    payout_type: PayoutType = PayoutType.CUMULATIVE
    tds_applicable: bool = False
    tds_rate: float = 0.0

class FDCreate(FDBase):
    pass

class FDSchema(FDBase):
    id: int
    user_id: int

    class Config:
        from_attributes = True
