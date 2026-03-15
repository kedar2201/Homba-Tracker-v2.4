from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from ..database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    mobile_number = Column(String, nullable=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String)
    message = Column(String)
    type = Column(String) # e.g., "PORTFOLIO_SUMMARY", "ALERT"
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")

class AlertSetting(Base):
    __tablename__ = "alert_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    stock_drop_pct = Column(Float, default=5.0) # Alert if any stock drops X%
    portfolio_drop_pct = Column(Float, default=3.0) # Alert if total portfolio drops X%
    nifty_drop_pct = Column(Float, default=2.0) # Alert if Nifty drops X%
    
    user = relationship("User")

class Tracklist(Base):
    __tablename__ = "tracklists"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    symbol = Column(String, index=True)
    target_price = Column(Float, nullable=True)
    trigger_dma50 = Column(Boolean, default=False) # Alert if price > 50DMA
    trigger_dma200 = Column(Boolean, default=False) # Alert if price > 200DMA
    last_triggered_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")
