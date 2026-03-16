from app.database import SessionLocal
from app.models.mutual_fund import MutualFund

db = SessionLocal()
funds = db.query(MutualFund).filter(MutualFund.holder == 'M').all()

print("ID | Current Name | Current Code")
print("-" * 100)
for f in funds:
    # Print the full line to avoid truncation
    print(f"{f.id} | {f.scheme_name} | {f.amfi_code}")
db.close()
