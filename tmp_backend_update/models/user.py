from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from ..database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    full_name = Column(String, nullable=True)
    email = Column(String, unique=True, index=True)
    mobile_number = Column(String, nullable=True)
    city = Column(String, nullable=True)
    country = Column(String, nullable=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    
    # Licensing & Anti-Viral Logic
    device_fingerprint = Column(String, index=True, nullable=True)
    is_verified = Column(Boolean, default=False)
    otp_code = Column(String, nullable=True)
    otp_expiry = Column(DateTime, nullable=True)
    
    license_status = Column(String, default="trial") # trial, active, expired, blocked
    trial_start_at = Column(DateTime, default=datetime.utcnow)
    trial_end_at = Column(DateTime, nullable=True)
    extension_count = Column(Integer, default=0) # Track number of 30-day extensions
    activation_code = Column(String, nullable=True)
    
    radar_mode = Column(String, default="balanced") # conservative, balanced, aggressive

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
    
    # Conditions
    dma50_condition = Column(String, default="IGNORE") # ABOVE, BELOW, IGNORE
    dma200_condition = Column(String, default="IGNORE") # ABOVE, BELOW, IGNORE
    dip_percent = Column(Float, default=8.0)
    rsi_threshold = Column(Float, default=38.0)
    near_50dma_percent = Column(Float, default=2.0)
    near_200dma_percent = Column(Float, default=3.0)
    breakout_enabled = Column(Boolean, default=True)
    
    min_confidence_score = Column(Integer, default=60)
    alert_mode = Column(String, default="digest") # instant, digest
    last_alert_score = Column(Integer, default=0)
    
    # Trigger Toggles
    trigger_dip = Column(Boolean, default=True)
    trigger_rsi = Column(Boolean, default=True)
    trigger_dma = Column(Boolean, default=True)
    trigger_breakout = Column(Boolean, default=True)
    trigger_score = Column(Boolean, default=True)
    
    # Custom Weights/Toggles per scrip (Overrides global if set)
    use_custom_weights = Column(Boolean, default=False)
    # If all weights are 0, it uses global
    weight_dip = Column(Integer, default=0)
    weight_rsi = Column(Integer, default=0)
    weight_dma = Column(Integer, default=0)
    weight_breakout = Column(Integer, default=0)
    weight_market_bonus = Column(Integer, default=0)
    weight_pe_discount = Column(Integer, default=0)
    weight_peg = Column(Integer, default=0)
    
    use_dip = Column(Boolean, default=True)
    use_rsi = Column(Boolean, default=True)
    use_dma = Column(Boolean, default=True)
    use_breakout = Column(Boolean, default=True)
    use_market_bonus = Column(Boolean, default=True)
    use_pe_discount = Column(Boolean, default=True)
    use_peg = Column(Boolean, default=True)
    
    # Sector & Quality Metrics
    sector_type = Column(String, default="standard") # standard, bank, nbfc, insurance
    roe = Column(Float, default=0.0)
    roce = Column(Float, default=0.0)
    nim = Column(Float, default=0.0) # For Banks/NBFC
    gnpa = Column(Float, default=0.0) # For Banks
    ev_growth = Column(Float, default=0.0) # For Insurance
    solvency_ratio = Column(Float, default=0.0) # For Insurance

    # Quality weights per scrip
    weight_roe = Column(Integer, default=0)
    weight_roce_nim_ev = Column(Integer, default=0) # Shared slot for 2nd quality metric
    weight_quality_3 = Column(Integer, default=0) # For GNPA/Solvency
    use_quality = Column(Boolean, default=True)

    # Risk weights per scrip
    weight_risk_pe = Column(Integer, default=0)
    weight_risk_earnings = Column(Integer, default=0)
    weight_risk_debt = Column(Integer, default=0)
    use_risk = Column(Boolean, default=True)

    last_triggered_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")

class RadarSignalLog(Base):
    __tablename__ = "radar_signal_log"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    symbol = Column(String, index=True)
    confidence_score = Column(Integer)
    signal_summary = Column(String) # JSON or descriptive text
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User")

class RadarScoringWeights(Base):
    __tablename__ = "radar_scoring_weights"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    
    # Technical Weights (Default total: 50) - Model-2Q
    weight_dip = Column(Integer, default=12)
    weight_rsi = Column(Integer, default=8)
    weight_dma = Column(Integer, default=12)
    weight_breakout = Column(Integer, default=12)
    weight_market_bonus = Column(Integer, default=6)
    
    # Valuation Weights (Default total: 20)
    weight_pe_discount = Column(Integer, default=12)
    weight_peg = Column(Integer, default=8)

    # Quality Weights (Default total: 20)
    weight_roe = Column(Integer, default=10)
    weight_roce_nim_ev = Column(Integer, default=10)
    weight_quality_3 = Column(Integer, default=0)
    
    # Risk Deduction Weights (Default total: 10)
    weight_risk_pe = Column(Integer, default=2)
    weight_risk_earnings = Column(Integer, default=4)
    weight_risk_debt = Column(Integer, default=4)
    
    # Toggles
    use_dip = Column(Boolean, default=True)
    use_rsi = Column(Boolean, default=True)
    use_dma = Column(Boolean, default=True)
    use_breakout = Column(Boolean, default=True)
    use_market_bonus = Column(Boolean, default=True)
    use_pe_discount = Column(Boolean, default=True)
    use_peg = Column(Boolean, default=True)
    use_quality = Column(Boolean, default=True)
    use_risk = Column(Boolean, default=True)

    user = relationship("User")
