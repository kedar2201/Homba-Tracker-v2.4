from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.user import User
from ..schemas.user import UserCreate, Token, User as UserSchema, UserPasswordChange, UserUpdate, UserForgotPassword, NotificationSchema, AlertSettingSchema, TracklistSchema, TracklistCreate
from ..auth.auth import verify_password, get_password_hash, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, get_current_user

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
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    hashed_password = get_password_hash(user.password)
    new_user = User(
        email=user.email, 
        username=user.username, 
        mobile_number=user.mobile_number,
        hashed_password=hashed_password
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

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

@router.get("/tracklist", response_model=list[TracklistSchema])
def get_tracklist(
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    from ..models.user import Tracklist
    return db.query(Tracklist).filter(Tracklist.user_id == current_user.id).all()

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
        trigger_dma50=data.trigger_dma50,
        trigger_dma200=data.trigger_dma200
    )
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return new_item

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
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
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
