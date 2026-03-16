from app.database import SessionLocal
from app.models.mutual_fund import MutualFund
from app.services.market_data import fetch_mf_nav

db = SessionLocal()

# Find SBI Nifty Index Fund entries
sbi_nifty_funds = db.query(MutualFund).filter(
    MutualFund.scheme_name.like('%SBI%Nifty%Index%')
).all()

print(f"Found {len(sbi_nifty_funds)} SBI Nifty Index Fund entries\n")
print("=" * 120)
print(f"{'ID':<5} | {'Scheme Name':<50} | {'Holder':<8} | {'ISIN':<15} | {'AMFI Code':<10} | {'Current NAV'}")
print("=" * 120)

for mf in sbi_nifty_funds:
    # Fetch current NAV
    nav = fetch_mf_nav(amfi_code=mf.amfi_code, isin=mf.isin)
    print(f"{mf.id:<5} | {mf.scheme_name[:50]:<50} | {(mf.holder or 'None'):<8} | {(mf.isin or 'None'):<15} | {(mf.amfi_code or 'None'):<10} | {nav}")

print("\n" + "=" * 120)
print("CHECKING CORRECT ISIN: INF200K01S35")
print("=" * 120)

# Check what NAV we get with the correct ISIN
correct_isin = "INF200K01S35"
nav_from_correct_isin = fetch_mf_nav(isin=correct_isin)
print(f"NAV for ISIN {correct_isin}: {nav_from_correct_isin}")

# Update the funds to use the correct ISIN
print("\n" + "=" * 120)
print("UPDATING SBI Nifty Index Fund entries with correct ISIN")
print("=" * 120)

for mf in sbi_nifty_funds:
    if mf.isin != correct_isin:
        print(f"\nID {mf.id} - {mf.scheme_name} (Holder: {mf.holder or 'None'})")
        print(f"  Old ISIN: {mf.isin or 'None'}")
        print(f"  New ISIN: {correct_isin}")
        mf.isin = correct_isin
        db.add(mf)

db.commit()
print("\n✓ Updated all SBI Nifty Index Fund entries with correct ISIN")

db.close()
