import yfinance as yf
ticker = "NEWGEN.NS"
t = yf.Ticker(ticker)
info = t.info
print(f"Symbol: {ticker}")
print(f"ROE: {info.get('returnOnEquity')}")
print(f"ROE Trailing: {info.get('returnOnEquityTrailing')}")
print(f"ROA: {info.get('returnOnAssets')}")
print(f"Operating Margins: {info.get('operatingMargins')}")
print(f"Profit Margins: {info.get('profitMargins')}")
