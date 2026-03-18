from app.database import SessionLocal
from app.models.fixed_deposit import FixedDeposit
from app.models.equity import Equity
from app.models.mutual_fund import MutualFund
from app.models.other_asset import OtherAsset

db = SessionLocal()

print("=== IMPORT VERIFICATION ===\n")

# Check FDs
fds = db.query(FixedDeposit).all()
print(f"Fixed Deposits: {len(fds)}")
print("Sample FDs:")
for fd in fds[:5]:
    print(f"  - {fd.bank_name} | {fd.fd_code} | ₹{fd.principal:,.0f} @ {fd.interest_rate}%")

# Check for any suspicious FDs (0% rate or weird bank names)
suspicious = [fd for fd in fds if fd.interest_rate == 0 or "SHARES" in fd.bank_name.upper()]
if suspicious:
    print(f"\n⚠️  WARNING: Found {len(suspicious)} suspicious FDs:")
    for fd in suspicious[:5]:
        print(f"  - {fd.bank_name} | Rate: {fd.interest_rate}%")
else:
    print("\n✓ No suspicious FDs found (all have valid rates and bank names)")

# Check Other Assets
others = db.query(OtherAsset).all()
print(f"\nOther Assets: {len(others)}")
print("Categories:")
from collections import Counter
cats = Counter([o.category.value for o in others])
for cat, count in cats.items():
    print(f"  - {cat}: {count}")

print("\nSample Other Assets:")
for o in others[:5]:
    print(f"  - [{o.category.value}] {o.name} | ₹{o.valuation:,.0f}")

db.close()
