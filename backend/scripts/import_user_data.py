import pandas as pd
from app.database import SessionLocal, engine
from app.models.user import User
from app.models.equity import Equity, Exchange
from app.models.fixed_deposit import FixedDeposit, CompoundingFrequency, PayoutType
from app.models.mutual_fund import MutualFund
from app.models.other_asset import OtherAsset
from datetime import date, datetime, timedelta
import traceback

def to_float(val):
    try:
        if pd.isna(val) or str(val).strip() == "": return 0.0
        val_str = str(val).strip()
        val_str = val_str.replace("₹", "").replace(",", "").replace("-", "0").replace(" ", "")
        if val_str == "" or val_str == ".": return 0.0
        return float(val_str)
    except:
        return 0.0

def to_date(val):
    try:
        if pd.isna(val) or str(val).strip() == "": return date.today()
        if isinstance(val, (datetime, date)): 
            return val.date() if isinstance(val, datetime) else val
        if isinstance(val, (int, float)):
            return (datetime(1899, 12, 30) + timedelta(days=int(val))).date()
        if isinstance(val, str):
            return pd.to_datetime(val).date()
        return date.today()
    except:
        return date.today()

def import_data():
    db = SessionLocal()
    try:
        print("STRICT RESET: Doing a fresh import with strict categorization...")
        from app.database import Base
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        
        from app.auth.auth import get_password_hash
        user = User(username="testuser1", email="test@example.com", hashed_password=get_password_hash("password123"))
        db.add(user)
        db.commit()
        db.refresh(user)
        user_id = user.id

        # 1. Stocks
        print("Importing Equities...")
        stock_path = "C:/Users/kedar/Downloads/NEW homba stocks 28 aug 2023.xlsx"
        df_eq = pd.read_excel(stock_path, sheet_name="all shares details 10 aug", header=None)
        start_row = 0
        for i, row in df_eq.iterrows():
            if pd.notna(row[2]) and "scrip" in str(row[2]).lower():
                start_row = i + 1
                break
        
        added_eq = 0
        seen_equities = set()
        for i in range(start_row, len(df_eq)):
            row = df_eq.iloc[i]
            holder = str(row[1]).strip().upper() if pd.notna(row[1]) else "UNKNOWN"
            symbol = row[2]
            qty_raw = row[7]
            price_raw = row[11] # Avg Buy Price
            ltp_raw = row[6]    # LTP (Standard LTP)
            # Some LTPs might be in Col 25 too, but Col 6 is standard here
            
            if pd.isna(symbol) or str(symbol).strip() == "": continue
            symbol_str = str(symbol).strip().upper()
            if any(x in symbol_str for x in ["TOTAL", "COMBINED", "SCRIP NAME"]): continue
            
            qty = to_float(qty_raw)
            if qty > 0:
                # Calculate Buy Price from Total Invested (Col 10) / Qty
                # Col 10 is 'Invested' based on analysis
                total_invested = to_float(row[10])
                unit_buy_price = total_invested / qty if qty else 0.0

                # Row uniqueness check
                row_key = (symbol_str, holder, qty, unit_buy_price, to_float(ltp_raw))
                if row_key in seen_equities: continue
                seen_equities.add(row_key)
                
                # Detection of Exchange (Purely numeric symbols are usually BSE)
                current_exc = Exchange.NSE
                if symbol_str.isdigit():
                    current_exc = Exchange.BSE

                eq = Equity(
                    user_id=user_id, exchange=current_exc, symbol=symbol_str,
                    holder=holder,
                    quantity=int(qty), buy_price=unit_buy_price,
                    buy_date=date(2023, 8, 1),
                    current_price=to_float(ltp_raw)
                )
                db.add(eq)
                added_eq += 1

        # 2. FD Sheet Strict Filter
        print("Importing from 'nov2023' - Full categorization...")
        from app.models.other_asset import OtherAsset, AssetCategory
        fd_path = "C:/Users/kedar/Downloads/fd23-24-Aug .xlsx"
        df_fd = pd.read_excel(fd_path, sheet_name="nov2023", header=None)
        start_row_fd = 0
        for i, row in df_fd.iterrows():
            if pd.notna(row[0]) and "code" in str(row[0]).lower():
                start_row_fd = i + 1
                break
        
        added_fds = 0
        added_mfs = 0
        added_others = 0
        used_fd_codes = set()
        
        # CATEGORY MAPPING (Priority ordered: Gold should be checked first)
        CAT_MAP = [
            ("gold", AssetCategory.GOLD),
            ("lic", AssetCategory.INSURANCE),
            ("insurance", AssetCategory.INSURANCE),
            ("ppf", AssetCategory.INSURANCE), # Moved to Insurance header per user request
            ("epf", AssetCategory.INSURANCE), # Moved to Insurance header per user request
            ("post office", AssetCategory.SAVINGS), # Moved to Savings header per user request
            ("bond", AssetCategory.BOND),
            ("saving", AssetCategory.SAVINGS),
            ("sb a/c", AssetCategory.SAVINGS),
            ("plot", AssetCategory.REAL_ESTATE),
            ("land", AssetCategory.REAL_ESTATE),
            ("flat", AssetCategory.REAL_ESTATE),
            ("shop", AssetCategory.REAL_ESTATE),
            ("office", AssetCategory.REAL_ESTATE),
            ("bhk", AssetCategory.REAL_ESTATE),
            ("asavari", AssetCategory.REAL_ESTATE),
            ("parle", AssetCategory.REAL_ESTATE),
            ("beach croft", AssetCategory.REAL_ESTATE),
        ]

        # KEYWORDS TO ABSOLUTELY IGNORE (Junk rows - summaries, totals, etc.)
        JUNK_KEYWORDS = ["total", "combined", "grand total", "rs", "uday", "cia", "usd", "bc", "loan", "shares", "equity", "nps"]

        for i in range(start_row_fd, len(df_fd)):
            row = df_fd.iloc[i]
            d_code = row[0]
            status = str(row[1]).lower() if pd.notna(row[1]) else ""
            d_name = row[2]
            fd_code_raw = row[3]
            s_dt_raw = row[4]
            m_dt_raw = row[5]
            p_raw = row[8]
            rate_raw = row[10]
            bank_val = row[12]
            
            p_val = to_float(p_raw)
            if p_val <= 0 or "matured" in status or pd.isna(d_name):
                continue
            
            name_str = str(d_name).lower().strip()
            bank_str = str(bank_val).lower().strip() if pd.notna(bank_val) else "unknown"
            rate_val = to_float(rate_raw)
            
            # 0. JUNK FILTER (Avoid rows that are just totals or codes)
            if any(k in name_str for k in JUNK_KEYWORDS) or any(k in bank_str for k in JUNK_KEYWORDS):
                continue

            # 1. CHECK FOR MUTUAL FUNDS & SGBs
            is_sgb = "sgb" in bank_str or "gold bond" in bank_str or "sgb" in name_str or "gold bond" in name_str
            if "mutual fund" in bank_str or name_str.startswith("mf-") or "fund" in name_str or is_sgb:
                # Extract holder from depositor code (Column 0)
                holder_mf = str(d_code).strip().upper() if pd.notna(d_code) else "UNKNOWN"
                
                # SGBs have units (qty) in Column 3 (fd_code_raw)
                # Interest is 2.5% per annum
                mf = MutualFund(
                    user_id=user_id, scheme_name=str(d_name), depositor_name=str(d_name), 
                    depositor_code=str(d_code)[:10], holder=holder_mf,
                    units=to_float(fd_code_raw), 
                    invested_amount=p_val, transaction_date=to_date(s_dt_raw),
                    interest_rate=2.5 if is_sgb else 0.0
                )
                db.add(mf)
                added_mfs += 1
                continue

            # 2. CHECK FOR OTHER CATEGORIES (Insurance, Gold, Shares etc)
            mapped_cat = None
            for key, cat in CAT_MAP:
                if key in name_str or key in bank_str:
                    mapped_cat = cat
                    break
            
            # 3. EXTRA CATEGORIZATION: If rate is 0 or bank name is weird (numbers, etc.)
            if not mapped_cat:
                if rate_val == 0 or bank_str == "unknown" or bank_str == "" or bank_str.replace(".","").isnumeric():
                    mapped_cat = AssetCategory.MISC
                    if "saving" in bank_str: mapped_cat = AssetCategory.SAVINGS

            if mapped_cat:
                oa = OtherAsset(
                    user_id=user_id, category=mapped_cat,
                    name=str(d_name), institution=str(bank_val) if pd.notna(bank_val) else mapped_cat.value,
                    valuation=p_val, description=f"Code: {d_code} | Original Rate: {rate_val}%"
                )
                db.add(oa)
                added_others += 1
                continue

            # 4. IF IT REACHES HERE, IT MUST BE A VALID FD
            # Safety: Even if not mapped, if rate is 0, it's not an FD
            if rate_val == 0:
                continue

            s_date = to_date(s_dt_raw)
            raw_code = str(fd_code_raw).strip() if pd.notna(fd_code_raw) and str(fd_code_raw).strip() != "" else f"FD-{i}"
            unique_code = raw_code
            counter = 1
            while unique_code in used_fd_codes:
                unique_code = f"{raw_code}-{counter}"
                counter += 1
            used_fd_codes.add(unique_code)

            int_rate = rate_val
            if 0 < int_rate < 1:
                int_rate *= 100
            
            m_date = to_date(m_dt_raw)
            
            fd = FixedDeposit(
                user_id=user_id, bank_name=str(bank_val).upper()[:50] if pd.notna(bank_val) else "UNKNOWN BANK",
                depositor_name=str(d_name)[:100], depositor_code=str(d_code)[:10],
                fd_code=unique_code, principal=p_val, interest_rate=int_rate,
                start_date=s_date, maturity_date=m_date,
                compounding_frequency=CompoundingFrequency.QUARTERLY, payout_type=PayoutType.CUMULATIVE
            )
            db.add(fd)
            added_fds += 1
        
        db.commit()
        print(f"COMPLETE: {added_eq} Equities, {added_fds} FDs, {added_mfs} MFs, and {added_others} Other Assets.")
    except Exception:
        db.rollback()
        print("ERROR: Import failed.")
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    import_data()
