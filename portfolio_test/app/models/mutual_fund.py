from sqlalchemy import Column, Integer, String, Float, Date, Enum, ForeignKey
from sqlalchemy.orm import relationship
from ..database import Base
import enum

class MFStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    SOLD = "SOLD"

class MutualFund(Base):
    __tablename__ = "mutual_funds"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    scheme_name = Column(String, index=True)
    depositor_name = Column(String, index=True)
    depositor_code = Column(String, index=True)
    holder = Column(String, nullable=True)  # K/S/M/H
    isin = Column(String, index=True)
    units = Column(Float)
    invested_amount = Column(Float)
    transaction_date = Column(Date)
    amc_name = Column(String, nullable=True)
    amfi_code = Column(String, nullable=True)
    interest_rate = Column(Float, nullable=True, default=0.0) # For SGBs: 2.5%
    
    # Portfolio Units (Distinct from 'units' which is quantity)
    p_buy_units = Column(Float, default=0.0)
    p_sell_units = Column(Float, default=0.0)
    
    # Sell tracking
    status = Column(Enum(MFStatus), default=MFStatus.ACTIVE, nullable=False)
    sell_nav = Column(Float, nullable=True)
    sell_date = Column(Date, nullable=True)

    user = relationship("User")
