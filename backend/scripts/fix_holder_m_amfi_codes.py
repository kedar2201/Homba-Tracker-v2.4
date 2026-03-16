from app.database import SessionLocal
from app.models.mutual_fund import MutualFund
from app.services.market_data import search_mf_nav_by_name

db = SessionLocal()

# Get funds for holder M
m_funds = db.query(MutualFund).filter(MutualFund.holder == 'M').order_by(MutualFund.scheme_name).all()

print(f"Found {len(m_funds)} funds for holder M\n")
print("=" * 120)
print("UPDATING AMFI CODES TO DIRECT PLAN:")
print("=" * 120)

updates_made = 0

for mf in m_funds:
    # Search for Direct Plan version
    direct_plan_name = mf.scheme_name
    if "DIRECT PLAN" not in direct_plan_name.upper():
        direct_plan_name = f"{mf.scheme_name} - Direct Plan"
    
    print(f"\nFund: {mf.scheme_name}")
    print(f"  Current AMFI Code: {mf.amfi_code or 'None'}")
    print(f"  Searching for: {direct_plan_name}")
    
    # Search for the Direct Plan
    result = search_mf_nav_by_name(direct_plan_name)
    
    if result and isinstance(result, dict):
        new_code = result.get('code')
        new_nav = result.get('nav')
        
        if new_code and new_code != mf.amfi_code:
            print(f"  ✓ Found Direct Plan - NAV: {new_nav}, Code: {new_code}")
            print(f"  → Updating AMFI code from {mf.amfi_code} to {new_code}")
            
            mf.amfi_code = new_code
            db.add(mf)
            updates_made += 1
        else:
            print(f"  ℹ Same code or no change needed")
    else:
        print(f"  ✗ Direct Plan not found")

if updates_made > 0:
    db.commit()
    print(f"\n{'=' * 120}")
    print(f"✓ Updated {updates_made} funds to Direct Plan AMFI codes")
    print(f"{'=' * 120}")
else:
    print(f"\n{'=' * 120}")
    print("No updates needed")
    print(f"{'=' * 120}")

db.close()
