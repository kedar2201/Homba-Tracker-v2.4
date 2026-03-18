from app.database import SessionLocal
from app.models.equity import Equity
from app.models.mutual_fund import MutualFund
from app.services.market_data import fetch_mf_nav, search_mf_nav_by_name

def restore_all_units_pinpoint():
    db = SessionLocal()
    try:
        print("Starting PINPOINT PF Units Restoration for User 2...")
        
        # --- 1. EQUITIES (User 2) ---
        target_u2_eq_units = 479635.15
        u2_eqs = db.query(Equity).filter(Equity.user_id == 2).all()
        # Filter out Bonds
        u2_stocks = []
        u2_stock_total_val = 0
        for e in u2_eqs:
            is_sgb = e.symbol.startswith("SGB") or (e.scrip_name and "SGB" in e.scrip_name.upper())
            if is_sgb:
                e.buy_units = 0.0
                e.sell_units = 0.0
            else:
                val = (e.current_price or e.buy_price or 0) * e.quantity
                u2_stock_total_val += val
                u2_stocks.append((e, val))
        
        if u2_stock_total_val > 0:
            # Scale each stock: its_value * (target_total_units / total_value)
            scaling_factor = target_u2_eq_units / u2_stock_total_val
            for e, val in u2_stocks:
                e.buy_units = val * scaling_factor
                e.sell_units = 0.0
            print(f"User 2 Equity: Restored to exactly {target_u2_eq_units} units across {len(u2_stocks)} stocks.")

        # --- 2. MUTUAL FUNDS (User 2) ---
        target_u2_mf_units = 225100.7508
        u2_mfs = db.query(MutualFund).filter(MutualFund.user_id == 2).all()
        valid_u2_mfs = []
        u2_mf_total_val = 0
        for m in u2_mfs:
            is_sgb = "sgb" in m.scheme_name.lower() or (m.interest_rate and m.interest_rate > 0)
            if is_sgb:
                m.p_buy_units = 0.0
                m.p_sell_units = 0.0
                continue
                
            # Get current valuation
            nav = None
            if m.amfi_code or m.isin:
                nav = fetch_mf_nav(amfi_code=m.amfi_code, isin=m.isin)
            if nav is None:
                res = search_mf_nav_by_name(m.scheme_name)
                if res and isinstance(res, dict): nav = res.get('nav')
                elif res: nav = res
            
            if nav and nav > 0:
                current_val = nav * m.units
            else:
                current_val = m.invested_amount or 0
            
            u2_mf_total_val += current_val
            valid_u2_mfs.append((m, current_val))
            
        if u2_mf_total_val > 0:
            scaling_factor = target_u2_mf_units / u2_mf_total_val
            for m, val in valid_u2_mfs:
                m.p_buy_units = val * scaling_factor
                m.p_sell_units = 0.0
            print(f"User 2 MF: Restored to exactly {target_u2_mf_units} units across {len(valid_u2_mfs)} funds.")


        # --- 3. OTHER USERS (User 1 etc) ---
        # Set to standard 100 baseline for simplicity
        others_eq = db.query(Equity).filter(Equity.user_id != 2).all()
        for e in others_eq:
            is_sgb = e.symbol.startswith("SGB") or (e.scrip_name and "SGB" in e.scrip_name.upper())
            if is_sgb:
                e.buy_units = 0.0
            else:
                price = e.current_price or e.buy_price or 0
                e.buy_units = (price * e.quantity) / 100.0
            e.sell_units = 0.0
            
        others_mf = db.query(MutualFund).filter(MutualFund.user_id != 2).all()
        for m in others_mf:
            is_sgb = "sgb" in m.scheme_name.lower() or (m.interest_rate and m.interest_rate > 0)
            if is_sgb:
                m.p_buy_units = 0.0
            else:
                # Default: use current value / 100
                nav = fetch_mf_nav(amfi_code=m.amfi_code, isin=m.isin)
                if nav and nav > 0: val = nav * m.units
                else: val = m.invested_amount or 0
                m.p_buy_units = val / 100.0
            m.p_sell_units = 0.0

        db.commit()
        print("PINPOINT RESTORE COMPLETE.")
        
        # Verification Summary
        u2_check_eq = db.query(Equity).filter(Equity.user_id == 2).all()
        u2_check_mf = db.query(MutualFund).filter(MutualFund.user_id == 2).all()
        print(f"User 2 FINAL - Equity Units: {sum(e.buy_units for e in u2_check_eq):.8f}")
        print(f"User 2 FINAL - MF Units: {sum(m.p_buy_units for m in u2_check_mf):.8f}")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    restore_all_units_pinpoint()
