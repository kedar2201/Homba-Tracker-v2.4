import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import Optional
from ..database import get_db
from ..models.user import User
from ..schemas.user import UserCreate, UserRegister, Token, User as UserSchema, UserPasswordChange, UserUpdate, UserForgotPassword, NotificationSchema, AlertSettingSchema, TracklistSchema, TracklistCreate, RadarScoringSchema, LicenseStatus, UpdateLicenseRequest
from ..core.security import verify_password, get_password_hash, create_access_token
from ..auth.auth import get_current_user
from datetime import datetime, timedelta
import random

from ..core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["Authentication"],
)


@router.get("/ping")
def ping():
    return {"status": "auth alive"}

@router.get("/me", response_model=UserSchema)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/register", response_model=UserSchema)
def register_user(user: UserRegister, db: Session = Depends(get_db)):
    # 1. Check if user already exists
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    # 2. Skip fingerprint check for testing (Allow multiple accounts per device)
    """
    existing_device = db.query(User).filter(User.device_fingerprint == user.device_fingerprint).first()
    if existing_device:
        raise HTTPException(
            status_code=400, 
            detail="This device has already been used for a trial. Please login with your original account."
        )
    """

    # 3. Create New User
    hashed_password = get_password_hash(user.password)
    new_user = User(
        username=user.username,
        full_name=user.full_name,
        email=user.email, 
        mobile_number=user.mobile_number,
        city=user.city,
        country=user.country,
        hashed_password=hashed_password,
        device_fingerprint=user.device_fingerprint,
        is_verified=False, # Default to false, verify via OTP
        license_status="trial",
        trial_start_at=datetime.utcnow(),
        trial_end_at=datetime.utcnow() + timedelta(days=settings.FREE_TRIAL_DAYS)
    )

    
    # 4. Generate OTP (For testing phase, using a fixed 123456)
    # TODO: Replace with real email/SMS service in production
    otp = "123456"
    new_user.otp_code = otp
    new_user.otp_expiry = datetime.utcnow() + timedelta(hours=24) # Extended for testing
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    logger.info(f"New User Registered: {new_user.username} (OTP: {otp})")
    return new_user

@router.post("/verify-otp")
def verify_otp(username: str, otp: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Allow master OTP if configured (for development/testing)
    if user.otp_code != otp and (settings.DEFAULT_OTP is None or otp != settings.DEFAULT_OTP):
        raise HTTPException(status_code=400, detail="Invalid OTP")
    
    # Only check expiry for the real OTP code, or allow it for master OTP
    if (settings.DEFAULT_OTP is None or otp != settings.DEFAULT_OTP) and datetime.utcnow() > user.otp_expiry:
        raise HTTPException(status_code=400, detail="OTP expired")

    
    user.is_verified = True
    user.otp_code = None
    db.commit()
    return {"message": "Verification successful"}

@router.get("/license-check", response_model=LicenseStatus)
def check_license(current_user: User = Depends(get_current_user)):
    now = datetime.utcnow()
    
    # Calculate days left
    days_left = 0
    if current_user.trial_end_at:
        delta = current_user.trial_end_at - now
        days_left = max(0, delta.days)
    
    status = current_user.license_status
    
    # Auto-expire logic
    if status == "trial" and days_left <= 0:
        status = "expired"
    
    message = f"You are on a {status} license. {days_left} days remaining."
    if status == "expired":
        message = "Your trial has expired. Please contact administrator."
    elif status == "active":
        message = "Your account is fully active."


    return {
        "status": status,
        "trial_days_left": days_left,
        "trial_start_at": current_user.trial_start_at,
        "trial_end_at": current_user.trial_end_at,
        "is_verified": current_user.is_verified,
        "is_admin": current_user.is_admin,
        "message": message
    }

@router.post("/activate")
def activate_user(
    data: UpdateLicenseRequest, 
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """ADMIN: Hard activate a user (Permanent Active)"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
        
    user = db.query(User).filter(User.username == data.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
         
    user.license_status = "active"
    user.is_verified = True
    user.trial_end_at = None # PERMANENT access has no expiry date
    db.commit()
    logger.info(f"ADMIN {current_user.username} activated user {data.username}")
    return {"message": f"User {data.username} fully activated (Permanent)"}

@router.post("/update-license")
def update_license(
    data: UpdateLicenseRequest, 
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """ADMIN: Update status and/or expiry in one call (Body payload)."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
        
    user = db.query(User).filter(User.username == data.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if data.status in ["active", "trial", "blocked", "expired"]:
        user.license_status = data.status
    
    if data.expiry_days is not None:
        if data.expiry_days < 0:
            user.trial_end_at = None # No expiry
        else:
            user.trial_end_at = datetime.utcnow() + timedelta(days=data.expiry_days)
            if data.status == "trial":
                user.extension_count = (user.extension_count or 0) + 1
            
    db.commit()
    logger.info(f"ADMIN {current_user.username} updated license for {data.username}")
    return {"message": f"License updated for {data.username}", "new_status": user.license_status}

@router.put("/profile", response_model=UserSchema)
async def update_profile(
    data: UserUpdate, 
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    if data.email:
        current_user.email = data.email
    if data.mobile_number is not None:
        current_user.mobile_number = data.mobile_number
    if data.username:
        # Check if username exists
        existing = db.query(User).filter(User.username == data.username, User.id != current_user.id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Username already taken")
        current_user.username = data.username
    
    db.commit()
    db.refresh(current_user)
    return current_user

@router.get("/notifications", response_model=list[NotificationSchema])
def get_notifications(
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    from ..models.user import Notification
    return db.query(Notification).filter(Notification.user_id == current_user.id).order_by(Notification.created_at.desc()).limit(10).all()

@router.get("/alert-settings", response_model=AlertSettingSchema)
def get_alert_settings(
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    from ..models.user import AlertSetting
    settings = db.query(AlertSetting).filter(AlertSetting.user_id == current_user.id).first()
    if not settings:
        # Create default
        settings = AlertSetting(user_id=current_user.id)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings

@router.put("/alert-settings", response_model=AlertSettingSchema)
def update_alert_settings(
    data: AlertSettingSchema,
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    from ..models.user import AlertSetting
    settings = db.query(AlertSetting).filter(AlertSetting.user_id == current_user.id).first()
    if not settings:
        settings = AlertSetting(user_id=current_user.id)
        db.add(settings)
    
    settings.stock_drop_pct = data.stock_drop_pct
    settings.portfolio_drop_pct = data.portfolio_drop_pct
    settings.nifty_drop_pct = data.nifty_drop_pct
    
    db.commit()
    db.refresh(settings)
    return settings

@router.get("/radar-config", response_model=RadarScoringSchema)
def get_radar_config(
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    from ..models.user import RadarScoringWeights
    config = db.query(RadarScoringWeights).filter(RadarScoringWeights.user_id == current_user.id).first()
    if not config:
        config = RadarScoringWeights(user_id=current_user.id)
        db.add(config)
        db.commit()
        db.refresh(config)
    return config

@router.put("/radar-config", response_model=RadarScoringSchema)
def update_radar_config(
    data: RadarScoringSchema,
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    from ..models.user import RadarScoringWeights
    config = db.query(RadarScoringWeights).filter(RadarScoringWeights.user_id == current_user.id).first()
    if not config:
        config = RadarScoringWeights(user_id=current_user.id)
        db.add(config)
    
    # Update fields
    for field, value in data.dict().items():
        setattr(config, field, value)
    
    db.commit()
    db.refresh(config)
    return config

@router.get("/tracklist", response_model=list[TracklistSchema])
def get_tracklist(
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    from ..models.user import Tracklist
    items = db.query(Tracklist).filter(Tracklist.user_id == current_user.id).all()
    
    # Fetch User's scoring config
    from ..models.user import RadarScoringWeights
    scoring_config = db.query(RadarScoringWeights).filter(RadarScoringWeights.user_id == current_user.id).first()
    if not scoring_config:
        scoring_config = RadarScoringWeights(user_id=current_user.id)
        db.add(scoring_config)
        db.commit()
        db.refresh(scoring_config)

    from ..models.market_data import PriceCache
    from ..services.radar_engine import radar_engine
    
    # Enrich with live data from PriceCache
    results = []
    for item in items:
        # Create a dictionary from the model instance
        item_dict = {
            "id": item.id,
            "user_id": item.user_id,
            "symbol": item.symbol,
            "target_price": item.target_price,
            "dma50_condition": item.dma50_condition,
            "dma200_condition": item.dma200_condition,
            "dip_percent": item.dip_percent,
            "rsi_threshold": item.rsi_threshold,
            "near_50dma_percent": item.near_50dma_percent,
            "near_200dma_percent": item.near_200dma_percent,
            "breakout_enabled": item.breakout_enabled,
            "min_confidence_score": item.min_confidence_score,
            "alert_mode": item.alert_mode,
            "trigger_dip": item.trigger_dip,
            "trigger_rsi": item.trigger_rsi,
            "trigger_dma": item.trigger_dma,
            "trigger_breakout": item.trigger_breakout,
            "trigger_score": item.trigger_score,
            "last_triggered_at": item.last_triggered_at,
            "created_at": item.created_at,
            
            # Model-2Q Data
            "sector_type": item.sector_type or "standard",
            "roe": item.roe or 0.0,
            "roce": item.roce or 0.0,
            "nim": item.nim or 0.0,
            "gnpa": item.gnpa or 0.0,
            "ev_growth": item.ev_growth or 0.0,
            "solvency_ratio": item.solvency_ratio or 0.0,
            
            # Model-2Q Weights/Toggles
            "use_custom_weights": item.use_custom_weights or False,
            "weight_dip": item.weight_dip or 0,
            "weight_rsi": item.weight_rsi or 0,
            "weight_dma": item.weight_dma or 0,
            "weight_breakout": item.weight_breakout or 0,
            "weight_market_bonus": item.weight_market_bonus or 0,
            "weight_pe_discount": item.weight_pe_discount or 0,
            "weight_peg": item.weight_peg or 0,
            "weight_roe": item.weight_roe or 0,
            "weight_roce_nim_ev": item.weight_roce_nim_ev or 0,
            "weight_quality_3": item.weight_quality_3 or 0,
            "weight_risk_pe": item.weight_risk_pe or 0,
            "weight_risk_earnings": item.weight_risk_earnings or 0,
            "weight_risk_debt": item.weight_risk_debt or 0,
            "use_quality": item.use_quality if item.use_quality is not None else True,
            "use_risk": item.use_risk if item.use_risk is not None else True,

            "current_price": None,
            "ma50": None,
            "ma200": None,
            "rsi": None,
            "high_30d": None,
            "confidence_score": 0,
            "signal_details": []
        }
        
        # Look up live data
        live = db.query(PriceCache).filter(PriceCache.symbol == item.symbol).first()
        if live:
            item_dict["current_price"] = live.price
            item_dict["ma50"] = live.ma50
            item_dict["ma200"] = live.ma200
            item_dict["rsi"] = live.rsi
            item_dict["high_30d"] = live.high_30d
            
            # Calculate live score (Signature: score, details, signals_met, breakdown, config)
            score, details, _, breakdown = radar_engine.calculate_score(item, live, db, scoring_config)
            item_dict["confidence_score"] = score
            item_dict["signal_details"] = details
            item_dict["score_breakdown"] = breakdown
            
        results.append(item_dict)
        
    return results

@router.post("/tracklist", response_model=TracklistSchema)
def add_to_tracklist(
    data: TracklistCreate,
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    from ..models.user import Tracklist
    # Logic: Limit to 25 stocks as requested
    count = db.query(Tracklist).filter(Tracklist.user_id == current_user.id).count()
    if count >= 25:
        raise HTTPException(status_code=400, detail="Tracklist limit reached (max 25)")
    
    new_item = Tracklist(
        user_id=current_user.id,
        symbol=data.symbol.upper(),
        target_price=data.target_price,
        dma50_condition=data.dma50_condition or "IGNORE",
        dma200_condition=data.dma200_condition or "IGNORE",
        dip_percent=data.dip_percent,
        rsi_threshold=data.rsi_threshold,
        near_50dma_percent=data.near_50dma_percent,
        near_200dma_percent=data.near_200dma_percent,
        breakout_enabled=data.breakout_enabled,
        min_confidence_score=data.min_confidence_score,
        alert_mode=data.alert_mode,
        trigger_dip=data.trigger_dip,
        trigger_rsi=data.trigger_rsi,
        trigger_dma=data.trigger_dma,
        trigger_breakout=data.trigger_breakout,
        trigger_score=data.trigger_score,
        
        # Model-2Q
        sector_type=data.sector_type,
        roe=data.roe, roce=data.roce, nim=data.nim,
        gnpa=data.gnpa, ev_growth=data.ev_growth, solvency_ratio=data.solvency_ratio,
        use_custom_weights=data.use_custom_weights,
        weight_dip=data.weight_dip, weight_rsi=data.weight_rsi, weight_dma=data.weight_dma,
        weight_breakout=data.weight_breakout, weight_market_bonus=data.weight_market_bonus,
        weight_pe_discount=data.weight_pe_discount, weight_peg=data.weight_peg,
        weight_roe=data.weight_roe, weight_roce_nim_ev=data.weight_roce_nim_ev,
        weight_quality_3=data.weight_quality_3,
        weight_risk_pe=data.weight_risk_pe, weight_risk_earnings=data.weight_risk_earnings,
        weight_risk_debt=data.weight_risk_debt,
        use_quality=data.use_quality, use_risk=data.use_risk
    )
    db.add(new_item)
    
    # Ensure PriceCache entry exists for this symbol
    from ..models.market_data import PriceCache
    from ..services.analytics import analytics_service
    
    existing_cache = db.query(PriceCache).filter(PriceCache.symbol == new_item.symbol).first()
    if not existing_cache:
        new_cache = PriceCache(symbol=new_item.symbol)
        db.add(new_cache)
        db.commit() # Commit so analytics_service can find it
        
    # Trigger immediate analytics update for this specific scrip so the Radar gets data quickly
    try:
        analytics_service.update_analytics(db, new_item.symbol)
    except Exception as e:
        logger.error(f"Failed to trigger analytics update for new tracklist item {new_item.symbol}: {e}")

    db.commit()
    db.refresh(new_item)
    return new_item

@router.put("/tracklist/{item_id}", response_model=TracklistSchema)
def update_tracklist_item(
    item_id: int,
    data: TracklistCreate,
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    from ..models.user import Tracklist
    item = db.query(Tracklist).filter(Tracklist.id == item_id, Tracklist.user_id == current_user.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    item.target_price = data.target_price
    item.dma50_condition = data.dma50_condition
    item.dma200_condition = data.dma200_condition
    item.dip_percent = data.dip_percent
    item.rsi_threshold = data.rsi_threshold
    item.near_50dma_percent = data.near_50dma_percent
    item.near_200dma_percent = data.near_200dma_percent
    item.breakout_enabled = data.breakout_enabled
    item.min_confidence_score = data.min_confidence_score
    item.alert_mode = data.alert_mode
    item.trigger_dip = data.trigger_dip
    item.trigger_rsi = data.trigger_rsi
    item.trigger_dma = data.trigger_dma
    item.trigger_breakout = data.trigger_breakout
    item.trigger_score = data.trigger_score
    
    # Model-2Q
    item.sector_type = data.sector_type
    item.roe = data.roe
    item.roce = data.roce
    item.nim = data.nim
    item.gnpa = data.gnpa
    item.ev_growth = data.ev_growth
    item.solvency_ratio = data.solvency_ratio
    item.use_custom_weights = data.use_custom_weights
    item.weight_dip = data.weight_dip
    item.weight_rsi = data.weight_rsi
    item.weight_dma = data.weight_dma
    item.weight_breakout = data.weight_breakout
    item.weight_market_bonus = data.weight_market_bonus
    item.weight_pe_discount = data.weight_pe_discount
    item.weight_peg = data.weight_peg
    item.weight_roe = data.weight_roe
    item.weight_roce_nim_ev = data.weight_roce_nim_ev
    item.weight_quality_3 = data.weight_quality_3
    item.weight_risk_pe = data.weight_risk_pe
    item.weight_risk_earnings = data.weight_risk_earnings
    item.weight_risk_debt = data.weight_risk_debt
    item.use_quality = data.use_quality
    item.use_risk = data.use_risk
    
    # Reset last_triggered_at if parameters change? Probably yes so it can trigger again
    item.last_triggered_at = None
    
    db.commit()
    db.refresh(item)
    return item

@router.get("/price-check/{symbol}")
def quick_price_check(symbol: str, db: Session = Depends(get_db)):
    """
    Fetch live price and DMA for a symbol.
    Symbol resolution order:
      1. Exact match in PriceCache (may already have a verified yahoo_symbol)
      2. Match from equity portfolio table (user's own holdings — most reliable mapping)
      3. Fall back to appending .NS
    Always force-refreshes analytics so the user sees live data.
    """
    from ..services.analytics import analytics_service
    from ..models.market_data import PriceCache
    from ..models.equity import Equity
    from datetime import datetime, timedelta
    import yfinance as yf

    s = symbol.upper()

    # ── Step 1: Get or create PriceCache entry ──────────────────────────────
    entry = db.query(PriceCache).filter(PriceCache.symbol == s).first()
    if not entry:
        entry = PriceCache(symbol=s)
        db.add(entry)
        db.commit()

    # ── Step 2: Resolve best yahoo_symbol ───────────────────────────────────
    if not entry.yahoo_symbol or not entry.yahoo_symbol_locked:
        # Check equity portfolio for a known mapping (user's own holdings)
        equity_row = db.query(Equity).filter(Equity.symbol == s).first()
        if equity_row and equity_row.yahoo_symbol:
            entry.yahoo_symbol = equity_row.yahoo_symbol
            logger.info(f"[price-check] Using equity portfolio yahoo_symbol for {s}: {equity_row.yahoo_symbol}")
        elif not entry.yahoo_symbol:
            # Default guess
            entry.yahoo_symbol = f"{s}.NS"
            logger.info(f"[price-check] Guessing yahoo_symbol for {s}: {entry.yahoo_symbol}")
        db.commit()

    # ── Step 3: Always force-refresh analytics (live data) ──────────────────
    try:
        analytics_service.update_analytics(db, s)
        db.refresh(entry)
    except Exception as e:
        logger.warning(f"[price-check] analytics update failed for {s}: {e}")

    if not entry or not entry.price or entry.price == 0:
        raise HTTPException(status_code=404, detail=f"Price data not available for '{s}'. Check the symbol (use NSE format, e.g. RELIANCE not RELIANCE.NS).")

    # ── Step 4: Back-fill fundamentals if still missing ─────────────────────
    if not entry.roe or entry.roe == 0 or not entry.roce or entry.roce == 0:
        try:
            yf_sym = entry.yahoo_symbol or f"{s}.NS"
            ticker = yf.Ticker(yf_sym)
            info = ticker.info
            roe_val = info.get('returnOnEquity', 0)
            roa_val = info.get('returnOnAssets', 0)
            if roe_val: entry.roe = float(roe_val) * 100
            if roa_val: entry.roce = float(roa_val) * 135
            if not entry.peg_ratio: entry.peg_ratio = info.get('pegRatio')
            if not entry.pe: entry.pe = info.get('trailingPE')
            db.commit()
            db.refresh(entry)
        except Exception as e:
            logger.warning(f"[price-check] fundamentals back-fill failed for {s}: {e}")

    logger.info(f"[price-check] {s}: price={entry.price}, ROE={entry.roe}, ROCE={entry.roce}, yahoo={entry.yahoo_symbol}")

    return {
        "symbol": entry.symbol,
        "yahoo_symbol": entry.yahoo_symbol,
        "price": entry.price,
        "prev_close": entry.prev_close,
        "ma50": entry.ma50,
        "ma200": entry.ma200,
        "rsi": entry.rsi,
        "high_30d": entry.high_30d,
        "high_3m": entry.high_3m,
        "pe": entry.pe,
        "pe_avg_5y": entry.pe_avg_5y,
        "peg_ratio": entry.peg_ratio,
        "current_vol": entry.current_vol,
        "avg_vol_20d": entry.avg_vol_20d,
        "roe": entry.roe,
        "roce": entry.roce,
        "nim": entry.nim,
        "gnpa": entry.gnpa,
        "solvency_ratio": entry.solvency_ratio,
        "ev_growth": entry.ev_growth
    }

@router.delete("/tracklist/{item_id}")
def remove_from_tracklist(
    item_id: int,
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    from ..models.user import Tracklist
    item = db.query(Tracklist).filter(Tracklist.id == item_id, Tracklist.user_id == current_user.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(item)
    db.commit()
    return {"message": "Removed from tracklist"}

@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # BLOCK CHECK DURING LOGIN
    if user.license_status == "blocked":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been blocked by the administrator."
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=user.username, expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/change-password")
async def change_password(data: UserPasswordChange, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password incorrect")
    
    current_user.hashed_password = get_password_hash(data.new_password)
    db.commit()
    return {"message": "Password changed successfully"}

@router.post("/forgot-password")
async def forgot_password(data: UserForgotPassword, db: Session = Depends(get_db)):
    # Check if user exists
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        # For security, don't reveal if user exists or not, 
        # but the user requested "check your email" UI, so we'll be helpful.
        raise HTTPException(status_code=404, detail="Email not found")
    
    # In a real app, you'd generate a token and send an email here.
    # We will simulate success for now.
    return {"message": "Recovery link sent to your email"}

@router.get("/users", response_model=list[UserSchema])
def get_all_users(
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return db.query(User).all()

@router.post("/block-user")
def block_user(username: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.license_status = "blocked"
    db.commit()
    return {"message": f"User {username} blocked"}

@router.post("/extend-trial")
def extend_trial(username: str, days: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.trial_end_at:
        user.trial_end_at = datetime.utcnow()
    user.trial_end_at += timedelta(days=days)
    user.license_status = "trial" # Reset to trial if they were expired
    db.commit()
    return {"message": f"Trial extended by {days} days for {username}"}
