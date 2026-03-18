import os
from sqlalchemy import text
from app.database import SessionLocal
from app.models.rating import StockRatingSummary
from app.models.equity import Equity
from app.services.analytics import analytics_service
from app.services.rating_engine import compute_and_store_rating
from app.services.profitability_service import compute_and_store_profitability

def clean_symbol(sym):
    if not sym: return sym
    # Special case: don't clean index symbols
    if sym.startswith("^"): return sym
    
    res = sym.upper()
    # Strip prefixes
    for prefix in ["NSE:NSE:", "NSE:", "BSE:", "BOM:"]:
        if res.startswith(prefix):
            res = res[len(prefix):]
    
    # Strip suffixes (only if they are standard exchange ones)
    if res.endswith(".NS"): res = res[:-3]
    if res.endswith(".BO"): res = res[:-3]
    
    return res

def migrate_ratings():
    db = SessionLocal()
    print("Standardizing StockRatingSummary keys...")
    
    ratings = db.query(StockRatingSummary).all()
    
    # Map from clean_symbol -> rating_object
    # If duplicates, we keep the one that is RATED or has a higher star_rating
    cleaned_map = {}
    
    for r in ratings:
        clean = clean_symbol(r.scrip_code)
        if clean not in cleaned_map:
            cleaned_map[clean] = r
        else:
            existing = cleaned_map[clean]
            # Replace if new one is RATED and old isn't, or if higher star rating
            r_is_better = (r.data_state == "RATED" and existing.data_state != "RATED") or \
                          ((r.star_rating or 0) > (existing.star_rating or 0))
            if r_is_better:
                # We'll delete the old one later if it's a different physical record
                cleaned_map[clean] = r
    
    # Now we perform the actual migration in the DB
    # Safer way: Create a temporary list of new records, delete all old ones, insert new
    final_records = []
    for clean, r in cleaned_map.items():
        # Create a clean clone
        new_r = StockRatingSummary(
            scrip_code=clean,
            sector_type=r.sector_type,
            data_state=r.data_state,
            final_score=r.final_score,
            star_rating=r.star_rating,
            trend_score=r.trend_score,
            valuation_score=r.valuation_score,
            profitability_score=r.profitability_score,
            growth_score=r.growth_score,
            confidence_score=r.confidence_score,
            confidence_label=r.confidence_label,
            confidence_pts_have=r.confidence_pts_have,
            confidence_pts_max=r.confidence_pts_max,
            trend_confidence=r.trend_confidence,
            fallbacks_applied=r.fallbacks_applied,
            missing_fields=r.missing_fields,
            roe_3y_avg=r.roe_3y_avg,
            roce_3y_avg=r.roce_3y_avg,
            calculated_fy=r.calculated_fy
        )
        final_records.append(new_r)

    print(f"Migrating {len(ratings)} existing records to {len(final_records)} standardized records.")
    
    try:
        # 1. Clear existing
        db.execute(text("DELETE FROM stock_rating_summary"))
        db.commit()
        
        # 2. Add standardized
        for r in final_records:
            db.add(r)
        db.commit()
        print("Standardization successful.")
    except Exception as e:
        print(f"Error during migration: {e}")
        db.rollback()

    # 3. Ensure Equity table uses clean symbols too
    print("\nCleaning Equity table symbols...")
    equities = db.query(Equity).all()
    for e in equities:
        e.symbol = clean_symbol(e.symbol)
    db.commit()
    print("Equity table standardized.")

    db.close()

if __name__ == "__main__":
    migrate_ratings()
