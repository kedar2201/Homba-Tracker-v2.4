import yfinance as yf
print("Testing yfinance bulk download...")
symbols = ["^NSEI", "^BSESN"]
try:
    data = yf.download(symbols, period="5d", interval="1d", progress=False, auto_adjust=True)
    print(f"Data:\n{data}")
    if not data.empty:
        print("Success!")
    else:
        print("Empty DataFrame returned.")
except Exception as e:
    print(f"Error: {e}")
