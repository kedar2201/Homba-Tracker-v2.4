from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from ..database import Base

class NAVHistory(Base):
    __tablename__ = "nav_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    total_value = Column(Float)      # Market value of all active assets
    total_invested = Column(Float)   # Sum of buy prices
    nav_per_share = Column(Float)    # (total_value) / total_shares
    total_shares = Column(Integer)   # sum(quantity of active equities)
    mf_nav = Column(Float, default=0.0) # Total MF Value / Total MF Units
    
    user = relationship("User")
