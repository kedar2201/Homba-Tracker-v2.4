from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: Optional[str] = None
    mobile_number: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserRegister(UserCreate):
    device_fingerprint: str

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    mobile_number: Optional[str] = None
    username: Optional[str] = None

class User(UserBase):
    id: int
    is_active: bool = True
    is_admin: bool = False
    is_verified: bool = False
    license_status: str = "trial"
    trial_end_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class LicenseStatus(BaseModel):
    status: str # trial, active, expired, blocked
    trial_days_left: int
    is_verified: bool
    is_admin: bool
    message: Optional[str] = None

class NotificationSchema(BaseModel):
    id: int
    title: str
    message: str
    type: str
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True

class AlertSettingSchema(BaseModel):
    stock_drop_pct: float
    portfolio_drop_pct: float
    nifty_drop_pct: float

    class Config:
        from_attributes = True

class UpdateLicenseRequest(BaseModel):
    username: str
    status: Optional[str] = None
    expiry_days: Optional[int] = None

class TracklistBase(BaseModel):
    symbol: str
    target_price: Optional[float] = None
    dma50_condition: Optional[str] = "IGNORE"
    dma200_condition: Optional[str] = "IGNORE"
    dip_percent: float = 8.0
    rsi_threshold: float = 38.0
    near_50dma_percent: float = 2.0
    near_200dma_percent: float = 3.0
    breakout_enabled: bool = True
    min_confidence_score: int = 60
    alert_mode: str = "digest"
    trigger_dip: bool = True
    trigger_rsi: bool = True
    trigger_dma: bool = True
    trigger_breakout: bool = True
    trigger_score: bool = True
    use_custom_weights: bool = False
    
    # Model-2Q Qual & Sector
    sector_type: str = "standard"
    roe: float = 0.0
    roce: float = 0.0
    nim: float = 0.0
    gnpa: float = 0.0
    ev_growth: float = 0.0
    solvency_ratio: float = 0.0
    
    # Custom Overrides
    weight_dip: int = 0
    weight_rsi: int = 0
    weight_dma: int = 0
    weight_breakout: int = 0
    weight_market_bonus: int = 0
    weight_pe_discount: int = 0
    weight_peg: int = 0
    weight_roe: int = 0
    weight_roce_nim_ev: int = 0
    weight_quality_3: int = 0
    weight_risk_pe: int = 0
    weight_risk_earnings: int = 0
    weight_risk_debt: int = 0
    
    use_quality: bool = True
    use_risk: bool = True

class TracklistCreate(TracklistBase):
    pass

class TracklistSchema(TracklistBase):
    id: int
    user_id: int
    last_triggered_at: Optional[datetime] = None
    created_at: datetime
    
    # Live/Calculated data fields
    current_price: Optional[float] = None
    ma50: Optional[float] = None
    ma200: Optional[float] = None
    rsi: Optional[float] = None
    high_30d: Optional[float] = None
    confidence_score: Optional[int] = 0
    score_breakdown: Optional[dict] = None
    signal_details: Optional[list[str]] = []

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class UserPasswordChange(BaseModel):
    current_password: str
    new_password: str

class UserForgotPassword(BaseModel):
    email: EmailStr

class RadarScoringSchema(BaseModel):
    # Technical (50)
    weight_dip: int = 12
    weight_rsi: int = 8
    weight_dma: int = 12
    weight_breakout: int = 12
    weight_market_bonus: int = 6
    
    # Valuation (20)
    weight_pe_discount: int = 12
    weight_peg: int = 8

    # Quality (20) - Model-2Q
    weight_roe: int = 10
    weight_roce_nim_ev: int = 10
    weight_quality_3: int = 0
    
    # Risk (10)
    weight_risk_pe: int = 2
    weight_risk_earnings: int = 4
    weight_risk_debt: int = 4
    
    use_dip: bool = True
    use_rsi: bool = True
    use_dma: bool = True
    use_breakout: bool = True
    use_market_bonus: bool = True
    use_pe_discount: bool = True
    use_peg: bool = True
    use_quality: bool = True
    use_risk: bool = True

    class Config:
        from_attributes = True
