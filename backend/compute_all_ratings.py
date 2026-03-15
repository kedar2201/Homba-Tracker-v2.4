from app.database import SessionLocal
from app.models.market_data import PriceCache
from app.services import rating_engine as re_svc

db = SessionLocal()
symbols = [row.symbol for row in db.query(PriceCache).all() if row.symbol]
print(f"Found {len(symbols)} symbols in PriceCache")

for sym in symbols:
    r = re_svc.compute_and_store_rating(db, sym)
    if "error" not in r:
        print(f"{sym}: {r['star_rating']} stars  {r['final_score']}/100  ({r['label']})", flush=True)
    else:
        print(f"{sym}: SKIP - {r['error']}", flush=True)

db.close()
print("Done.")
