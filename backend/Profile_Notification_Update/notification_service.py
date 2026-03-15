import logging
from datetime import datetime
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..models.user import User, Notification
from ..models.equity import Equity
from ..services.calculations import get_equity_current_value

logger = logging.getLogger(__name__)

def generate_daily_portfolio_summaries():
    """
    Background task to calculate P/L for all users and generate notifications.
    Triggered at 3:45 PM (Market Close + 15 mins).
    """
    logger.info("[NotificationService] Starting daily portfolio summary generation...")
    db = SessionLocal()
    try:
        users = db.query(User).filter(User.is_active == True).all()
        
        for user in users:
            try:
                generate_user_summary(db, user)
            except Exception as e:
                logger.error(f"Failed to generate summary for user {user.username}: {e}")
                
        db.commit()
        logger.info(f"[NotificationService] Completed summaries for {len(users)} users.")
    finally:
        db.close()

def generate_user_summary(db: Session, user: User):
    """Calculate specific daily P/L for one user and store notification."""
    # 1. Calculate Equity Daily Gain
    equities = db.query(Equity).filter(Equity.user_id == user.id, Equity.status == "ACTIVE").all()
    
    total_market_value = 0
    total_daily_gain = 0
    
    for eq in equities:
        current_price = eq.current_price or 0
        prev_close = eq.prev_close or current_price
        
        market_value = current_price * eq.quantity
        daily_gain = (current_price - prev_close) * eq.quantity
        
        total_market_value += market_value
        total_daily_gain += daily_gain

    # 2. Prepare Notification Message
    gain_arrow = "▲" if total_daily_gain >= 0 else "▼"
    gain_pct = (total_daily_gain / (total_market_value - total_daily_gain) * 100) if (total_market_value - total_daily_gain) > 0 else 0
    
    title = f"Market Close Report {datetime.now().strftime('%d %b')}"
    message = (
        f"Hi {user.username}, your portfolio closed at ₹{total_market_value:,.2f}. "
        f"Daily Movement: {gain_arrow} ₹{abs(total_daily_gain):,.2f} ({gain_pct:+.2f}%). "
        "Check the app for detailed scrip-wise analysis."
    )

    # 3. Save to DB
    notification = Notification(
        user_id=user.id,
        title=title,
        message=message,
        type="PORTFOLIO_SUMMARY"
    )
    db.add(notification)
    
    # 4. (SIMULATED) Send Email
    send_simulated_email(user.email, title, message)
    
    # 5. (SIMULATED) Send Push Notification
    send_simulated_push(user.id, title, message)

def send_simulated_email(email, title, message):
    logger.info(f"[EMAIL SIMULATION] Sending to {email} | Subject: {title} | Body: {message}")

def send_simulated_push(user_id, title, message):
    logger.info(f"[PUSH SIMULATION] Sending to User {user_id} | Title: {title} | Body: {message}")
