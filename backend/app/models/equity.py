from sqlalchemy import Column, Integer, String, Float, Date, Enum, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from ..database import Base
import enum

class Exchange(str, enum.Enum):
    NSE = "NSE"
    BSE = "BSE"

class EquityStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    SOLD = "SOLD"

class Equity(Base):
    __tablename__ = "equities"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    exchange = Column(Enum(Exchange))
    symbol = Column(String, index=True)
    holder = Column(String, nullable=True) # K/S/M/H
    quantity = Column(Integer)  # Can be float if partial shares allowed? Keeping int for Indian markets usually
    buy_price = Column(Float)
    buy_date = Column(Date)
    current_price = Column(Float, nullable=True)
    prev_close = Column(Float, nullable=True)
    isin = Column(String, nullable=True)
    broker = Column(String, nullable=True)
    instrument_type = Column(String, nullable=True)
    scrip_name = Column(String, nullable=True)
    
    # Yahoo Mapping
    yahoo_symbol = Column(String, nullable=True)
    yahoo_symbol_locked = Column(Boolean, default=False)
    
    # Portfolio Units
    buy_units = Column(Float, default=0.0)
    sell_units = Column(Float, default=0.0)
    
    # Sell tracking
    status = Column(Enum(EquityStatus), default=EquityStatus.ACTIVE, nullable=False)
    sell_price = Column(Float, nullable=True)
    sell_date = Column(Date, nullable=True)

    user = relationship("User")
