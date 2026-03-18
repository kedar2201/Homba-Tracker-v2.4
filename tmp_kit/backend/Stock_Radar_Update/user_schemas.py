from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr
    username: str
    mobile_number: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    mobile_number: Optional[str] = None
    username: Optional[str] = None

class User(UserBase):
    id: int
    is_active: bool = True

    class Config:
        from_attributes = True

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

class TracklistBase(BaseModel):
    symbol: str
    target_price: Optional[float] = None
    trigger_dma50: bool = False
    trigger_dma200: bool = False

class TracklistCreate(TracklistBase):
    pass

class TracklistSchema(TracklistBase):
    id: int
    user_id: int
    last_triggered_at: Optional[datetime] = None
    created_at: datetime

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
