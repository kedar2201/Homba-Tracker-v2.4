import yfinance as yf
import pandas as pd
import sys

STOCKS = [
    ('HDFC Bank',      'HDFCBANK.NS',  'Private Bank',     True),
    ('SBI',            'SBIN.NS',      'PSU Bank',         True),
    ('Reliance Inds',  'RELIANCE.NS',  'Oil & Gas',        False),
    ('TCS',            'TCS.NS',       'IT / Services',    False),
    ('Infosys',        'INFY.NS',      'IT / Services',    False),
    ('Maruti Suzuki',  'MARUTI.NS',    'Auto',             False),
    ('Sun Pharma',     'SUNPHARMA.NS', 'Pharma',           False),
    ('Titan Company',  'TITAN.NS',     'Consumer',         False),
    ('NTPC',           'NTPC.NS',      'PSU Energy',       False),
    ('Asian Paints',   'ASIANPAINT.NS','Consumer Mfg',     False),
]
TARGET_YEARS = [2023, 2024, 2025]

def get_col(df, yr):
    for col in df.columns:
        try:
            if col.year == yr: return col
        except: pass
    return None

def sv(df, key, col):
    if key not in df.index or col is None: return None
    v = df.loc[key, col]
    return None if pd.isna(v) else float(v)

lines = []
detail_lines = []

for name, sym, sector, is_bank in STOCKS:
    detail_lines.append(f"\n{'='*65}")
    detail_lines.append(f"  {name} ({sym})  |  Sector: {sector}  |  Bank: {is_bank}")
    detail_lines.append(f"{'='*65}")
    try:
        t = yf.Ticker(sym)
        inc = t.income_stmt
        bs  = t.balance_sheet
        roes, roces = {}, {}
        for yr in TARGET_YEARS:
            ic = get_col(inc, yr)
            bc = get_col(bs, yr)
            ni = sv(inc, 'Net Income', ic)
            eq = sv(bs, 'Stockholders Equity', bc) or sv(bs, 'Common Stock Equity', bc)
            if ni and eq and eq > 0:
                roes[yr] = round(ni/eq*100, 2)
                detail_lines.append(f"  FY{yr}: NI={ni/1e7:>10.1f} Cr  Equity={eq/1e7:>10.1f} Cr  ROE={roes[yr]:.2f}%")
            else:
                roes[yr] = None
                detail_lines.append(f"  FY{yr}: ROE=N/A (NI={ni}, Equity={eq})")

            if not is_bank:
                eb = sv(inc, 'EBIT', ic) or sv(inc, 'Operating Income', ic)
                ta = sv(bs, 'Total Assets', bc)
                cl = sv(bs, 'Current Liabilities', bc) or sv(bs, 'Total Current Liabilities', bc)
                if eb and ta and cl:
                    ce = ta - cl
                    roces[yr] = round(eb/ce*100, 2) if ce > 0 else None
                    detail_lines.append(f"          EBIT={eb/1e7:>10.1f} Cr  CE={ce/1e7:>10.1f} Cr  ROCE={roces[yr]:.2f}%" if roces[yr] else f"          ROCE=N/A (CE={ce/1e7:.1f} Cr)")
                else:
                    roces[yr] = None
                    detail_lines.append(f"          ROCE=N/A (missing EBIT/Assets/CL data)")
        
        rl  = [v for v in roes.values()  if v is not None]
        rcl = [v for v in roces.values() if v is not None]
        roe_avg  = round(sum(rl)/len(rl), 2)   if rl  else None
        roce_avg = round(sum(rcl)/len(rcl), 2) if rcl else None
        detail_lines.append(f"\n  >> ROE  3Y-Avg : {f'{roe_avg:.2f}%' if roe_avg is not None else 'N/A'}")
        detail_lines.append(f"  >> ROCE 3Y-Avg : {f'{roce_avg:.2f}%' if not is_bank and roce_avg is not None else ('N/A [BANK]' if is_bank else 'N/A')}")

        def f(v): return f"{v:.1f}%" if v is not None else "  N/A"
        bk = " [BANK]" if is_bank else ""
        lines.append("%-18s %-18s %7s %7s %7s %7s | %8s %8s %8s %8s%s" % (
            name, sector,
            f(roes.get(2023)), f(roes.get(2024)), f(roes.get(2025)), f(roe_avg),
            f(roces.get(2023)), f(roces.get(2024)), f(roces.get(2025)), f(roce_avg),
            bk))
    except Exception as e:
        detail_lines.append(f"  ERROR: {e}")
        lines.append(f"{name}: ERROR - {e}")

output = []
output.extend(detail_lines)
output.append("\n\n" + "="*105)
output.append("  SUMMARY TABLE")
output.append("="*105)
output.append("%-18s %-18s %7s %7s %7s %7s | %8s %8s %8s %8s" % ("Company","Sector","ROE23","ROE24","ROE25","ROE3Y","ROCE23","ROCE24","ROCE25","ROCE3Y"))
output.append("-"*105)
output.extend(lines)
output.append("="*105)
output.append("\nNote: All values computed from Yahoo Finance raw annual statements.")
output.append("ROE = Net Income / Stockholders Equity")
output.append("ROCE = EBIT / (Total Assets - Current Liabilities)")
output.append("3Y Avg: Arithmetic mean of FY2023, FY2024, FY2025")
output.append("[BANK] = Bank/NBFC: ROCE not applicable.")

full = "\n".join(output)
with open("roe_roce_validation.txt", "w", encoding="utf-8") as fh:
    fh.write(full)
print("Done! Results written to roe_roce_validation.txt")
print(full)
