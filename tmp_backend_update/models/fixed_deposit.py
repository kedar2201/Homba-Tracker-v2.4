from sqlalchemy import Column, Integer, String, Float, Date, Boolean, Enum, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
import enum
from ..database import Base

class CompoundingFrequency(str, enum.Enum):
    MONTHLY = "Monthly"
    QUARTERLY = "Quarterly"
    HALF_YEARLY = "Half-Yearly"
    YEARLY = "Yearly"
    MATURITY = "On Maturity"

class PayoutType(str, enum.Enum):
    CUMULATIVE = "Cumulative"
    MONTHLY_PAYOUT = "Monthly Payout"
    QUARTERLY_PAYOUT = "Quarterly Payout"
    HALF_YEARLY_PAYOUT = "Half-Yearly Payout"
    ANNUAL_PAYOUT = "Annual Payout"

class FixedDeposit(Base):
    __tablename__ = "fixed_deposits"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    bank_name = Column(String, index=True)
    depositor_name = Column(String, index=True)
    depositor_code = Column(String, index=True)
    fd_code = Column(String, index=True)
    principal = Column(Float)
    interest_rate = Column(Float)
    start_date = Column(Date)
    maturity_date = Column(Date)
    compounding_frequency = Column(Enum(CompoundingFrequency))
    payout_type = Column(Enum(PayoutType))
    tds_applicable = Column(Boolean, default=False)
    tds_rate = Column(Float, default=0.0)

    user = relationship("User")

    __table_args__ = (
        UniqueConstraint('user_id', 'fd_code', name='_user_fd_uc'),
    )
