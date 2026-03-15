import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from .services.nav_service import capture_all_users_nav

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()

from .services.portfolio_sync import sync_all_equities
from .services.rating_engine import compute_and_store_rating
from .services.notification_service import generate_daily_portfolio_summaries
from .models.market_data import PriceCache
from .database import SessionLocal

def wrapper_sync_equities():
    """Wrapper to handle DB session for sync_all_equities"""
    db = SessionLocal()
    try:
        sync_all_equities(db)
    except Exception as e:
        logger.error(f"Error in scheduled equity sync: {e}")
    finally:
        db.close()

def wrapper_compute_all_ratings():
    """Wrapper to compute ratings for all scrips in the background."""
    logger.info("[RatingScheduler] Starting full rating computation cycle...")
    db = SessionLocal()
    try:
        # Get all unique symbols from PriceCache
        symbols = [row.symbol for row in db.query(PriceCache.symbol).distinct().all() if row.symbol]
        count = 0
        for symbol in symbols:
            try:
                compute_and_store_rating(db, symbol)
                count += 1
            except Exception as e:
                logger.error(f"[RatingScheduler] Error computing rating for {symbol}: {e}")
        logger.info(f"[RatingScheduler] Completed computation for {count}/{len(symbols)} scrips.")
    finally:
        db.close()

def start_scheduler():
    if not scheduler.running:
        # Schedule NAV snapshot every 2 hours on weekdays (Mon-Fri)
        trigger_nav = CronTrigger(
            day_of_week='mon-fri', 
            hour='9,11,13,15', 
            minute='15'
        )
        
        scheduler.add_job(
            capture_all_users_nav,
            trigger=trigger_nav,
            id='nav_snapshot_job',
            name='Capture NAV Snapshot every 2 hours',
            replace_existing=True
        )

        # Schedule Market Close Report at 3:45 PM (Mon-Fri)
        trigger_notif = CronTrigger(day_of_week='mon-fri', hour=15, minute=45)
        scheduler.add_job(
            generate_daily_portfolio_summaries,
            trigger=trigger_notif,
            id='daily_summary_notification',
            name='Daily Portfolio Summary at 3:45 PM',
            replace_existing=True
        )

        # Schedule Price Sync every 5 minutes during market hours
        trigger_price = CronTrigger(
             day_of_week='mon-fri',
             hour='9-15',
             minute='*/5'
        )

        scheduler.add_job(
            wrapper_sync_equities,
            trigger=trigger_price,
            id='equity_price_sync_job',
            name='Sync Equity Prices every 5 mins',
            replace_existing=True
        )

        # Schedule Rating Computation nightly at 01:00 AM
        trigger_rating = CronTrigger(hour=1, minute=0)
        scheduler.add_job(
            wrapper_compute_all_ratings,
            trigger=trigger_rating,
            id='rating_compute_nightly',
            name='Nightly Stock Rating Re-computation',
            replace_existing=True
        )
        
        # Run sync once at startup
        scheduler.add_job(
            wrapper_sync_equities,
            id='equity_sync_startup',
            name='Sync Equity Prices on Startup'
        )
        
        # Also run NAV capture once at startup
        scheduler.add_job(
            capture_all_users_nav,
            id='nav_snapshot_startup',
            name='Capture NAV Snapshot on Startup'
        )

        # Run Rating Computation once at startup (with short delay via scheduler)
        scheduler.add_job(
            wrapper_compute_all_ratings,
            id='rating_compute_startup',
            name='Stock Rating Re-computation on Startup'
        )
        
        scheduler.start()
        logger.info("Background scheduler started (Equity Sync + NAV Snapshots + Ratings).")

def shutdown_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Background scheduler shut down.")
