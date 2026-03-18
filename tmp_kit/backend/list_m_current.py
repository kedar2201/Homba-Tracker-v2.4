from app.database import SessionLocal
from app.models.mutual_fund import MutualFund

db = SessionLocal()
funds = db.query(MutualFund).filter(MutualFund.holder == 'M').all()

print(f"{'ID':<5} | {'Scheme Name':<60} | {'AMFI Code':<10}")
print("-" * 80)
for f in funds:
    print(f"{f.id:<5} | {f.scheme_name:<60} | {f.amfi_code or 'None':<10}")
db.close()
