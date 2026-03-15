"""
Validation script: Compute 3-year ROE and ROCE for 10 Nifty-50 stocks
from different sectors. FY2023, FY2024, FY2025 (year ending Mar).
Bank / NBFC: ROE only. Others: ROE + ROCE.
"""

import yfinance as yf
import pandas as pd
from datetime import datetime

# ------------------------------------------------------------
# Stock universe with sector classification
# ------------------------------------------------------------
STOCKS = [
    # (name, yahoo_ticker, sector, is_bank)
    ("HDFC Bank",        "HDFCBANK.NS",  "Private Bank",     True),
    ("SBI",              "SBIN.NS",      "PSU Bank",         True),
    ("Reliance Inds",    "RELIANCE.NS",  "Oil & Gas (Mfg)",  False),
    ("TCS",              "TCS.NS",       "IT / Services",    False),
    ("Infosys",          "INFY.NS",      "IT / Services",    False),
    ("Maruti Suzuki",    "MARUTI.NS",    "Auto (Mfg)",       False),
    ("Sun Pharma",       "SUNPHARMA.NS", "Pharma (Mfg)",     False),
    ("Titan Company",    "TITAN.NS",     "Consumer",         False),
    ("NTPC",             "NTPC.NS",      "PSU Energy (Mfg)", False),
    ("Asian Paints",     "ASIANPAINT.NS","Consumer (Mfg)",   False),
]

# For Indian FYs ending March:
# FY2023 → year-end 2023-03-31 → yfinance annual col ~2023
# FY2024 → year-end 2024-03-31
# FY2025 → year-end 2025-03-31
TARGET_YEARS = [2023, 2024, 2025]

def get_col_for_year(df, target_year):
    """Pick the column whose year matches target_year."""
    for col in df.columns:
        # yfinance cols are Timestamps
        try:
            if col.year == target_year:
                return col
        except:
            pass
    return None

def safe_val(df, key, col):
    """Extract float from df or return None."""
    if key not in df.index or col is None:
        return None
    v = df.loc[key, col]
    if pd.isna(v):
        return None
    return float(v)

def compute_roe_roce(name, ticker_symbol, sector, is_bank):
    print(f"\n{'='*60}")
    print(f"  {name} ({ticker_symbol}) — {sector} | Bank: {is_bank}")
    print(f"{'='*60}")

    try:
        t = yf.Ticker(ticker_symbol)
        inc = t.income_stmt
        bs  = t.balance_sheet
    except Exception as e:
        print(f"  ERROR fetching data: {e}")
        return None

    if inc is None or inc.empty or bs is None or bs.empty:
        print("  ERROR: Empty statements.")
        return None

    roe_vals  = {}
    roce_vals = {}

    for yr in TARGET_YEARS:
        inc_col = get_col_for_year(inc, yr)
        bs_col  = get_col_for_year(bs,  yr)

        if inc_col is None:
            print(f"  FY{yr}: Income statement column NOT FOUND. Columns: {[c.year for c in inc.columns]}")
            continue
        if bs_col is None:
            print(f"  FY{yr}: Balance sheet column NOT FOUND. Columns: {[c.year for c in bs.columns]}")
            continue

        net_income = safe_val(inc, "Net Income", inc_col)
        
        # Multiple candidates for equity
        equity = (safe_val(bs, "Stockholders Equity", bs_col)
                  or safe_val(bs, "Common Stock Equity", bs_col)
                  or safe_val(bs, "Total Equity Gross Minority Interest", bs_col))

        # ROE
        if net_income is None or equity is None:
            print(f"  FY{yr}: ROE — missing data  (NI={net_income}, Eq={equity})")
            roe_vals[yr] = None
        elif equity <= 0:
            print(f"  FY{yr}: ROE — Negative equity ({equity/1e7:.1f} Cr), set NULL")
            roe_vals[yr] = None
        else:
            roe = (net_income / equity) * 100
            roe_vals[yr] = roe
            print(f"  FY{yr}: NI={net_income/1e7:>10.1f} Cr  Equity={equity/1e7:>10.1f} Cr  ROE={roe:.2f}%")

        # ROCE (skip for banks)
        if is_bank:
            continue

        ebit = (safe_val(inc, "EBIT", inc_col)
                or safe_val(inc, "Operating Income", inc_col))
        total_assets = safe_val(bs, "Total Assets", bs_col)
        curr_liab = (safe_val(bs, "Current Liabilities", bs_col)
                     or safe_val(bs, "Total Current Liabilities", bs_col))

        if ebit is None or total_assets is None or curr_liab is None:
            print(f"  FY{yr}: ROCE — missing data  (EBIT={ebit}, Assets={total_assets}, CL={curr_liab})")
            roce_vals[yr] = None
        else:
            cap_emp = total_assets - curr_liab
            if cap_emp <= 0:
                print(f"  FY{yr}: ROCE — Capital Employed ≤ 0 ({cap_emp/1e7:.1f} Cr), skip.")
                roce_vals[yr] = None
            else:
                roce = (ebit / cap_emp) * 100
                roce_vals[yr] = roce
                print(f"  FY{yr}: EBIT={ebit/1e7:>10.1f} Cr  CE={cap_emp/1e7:>10.1f} Cr  ROCE={roce:.2f}%")

    # Averages
    roe_list  = [v for v in roe_vals.values()  if v is not None]
    roce_list = [v for v in roce_vals.values() if v is not None]

    roe_avg  = sum(roe_list)  / len(roe_list)  if roe_list  else None
    roce_avg = sum(roce_list) / len(roce_list) if roce_list else None

    print(f"\n  ➤ ROE  3Y-Avg : {f'{roe_avg:.2f}%' if roe_avg  is not None else 'N/A'}")
    if is_bank:
        print(f"  ➤ ROCE 3Y-Avg : N/A (Bank — not calculated)")
    else:
        print(f"  ➤ ROCE 3Y-Avg : {f'{roce_avg:.2f}%' if roce_avg is not None else 'N/A'}")

    return {
        "name":    name,
        "ticker":  ticker_symbol,
        "sector":  sector,
        "is_bank": is_bank,
        "roe_fy23": roe_vals.get(2023),
        "roe_fy24": roe_vals.get(2024),
        "roe_fy25": roe_vals.get(2025),
        "roe_3y_avg": roe_avg,
        "roce_fy23": roce_vals.get(2023) if not is_bank else None,
        "roce_fy24": roce_vals.get(2024) if not is_bank else None,
        "roce_fy25": roce_vals.get(2025) if not is_bank else None,
        "roce_3y_avg": roce_avg if not is_bank else None,
    }


if __name__ == "__main__":
    results = []
    for stock in STOCKS:
        r = compute_roe_roce(*stock)
        if r:
            results.append(r)

    print("\n\n" + "="*90)
    print("  SUMMARY TABLE")
    print("="*90)
    hdr = f"{'Company':<18} {'Sector':<20} {'ROE23':>7} {'ROE24':>7} {'ROE25':>7} {'ROE3Y':>7} {'ROCE23':>8} {'ROCE24':>8} {'ROCE25':>8} {'ROCE3Y':>8}"
    print(hdr)
    print("-"*90)
    for r in results:
        def fmt(v): return f"{v:.1f}%" if v is not None else "  N/A "
        bank_mark = " [BANK]" if r["is_bank"] else ""
        print(
            f"{r['name']:<18} {r['sector']:<20} "
            f"{fmt(r['roe_fy23']):>7} {fmt(r['roe_fy24']):>7} {fmt(r['roe_fy25']):>7} {fmt(r['roe_3y_avg']):>7} "
            f"{fmt(r['roce_fy23']):>8} {fmt(r['roce_fy24']):>8} {fmt(r['roce_fy25']):>8} {fmt(r['roce_3y_avg']):>8}"
            f"{bank_mark}"
        )
    print("="*90)
