from pydantic import BaseModel
from datetime import date
from typing import Optional
from ..models.equity import Exchange

class EquityBase(BaseModel):
    exchange: Exchange
    symbol: str
    holder: Optional[str] = None
    quantity: int
    buy_price: float
    buy_date: Optional[date] = None
    current_price: Optional[float] = None
    isin: Optional[str] = None
    broker: Optional[str] = None
    instrument_type: Optional[str] = None
    scrip_name: Optional[str] = None
    yahoo_symbol: Optional[str] = None
    yahoo_symbol_locked: Optional[bool] = False

class EquityCreate(EquityBase):
    pass

class EquitySchema(EquityBase):
    id: int
    user_id: int
    buy_units: Optional[float] = 0.0
    sell_units: Optional[float] = 0.0

    class Config:
        from_attributes = True
