import yfinance as yf
import pandas as pd

def test_yfinance():
    symbols = ["RELIANCE.NS", "HDFC.NS", "^NSEI"]
    print(f"Testing download for: {symbols}")
    
    try:
        data = yf.download(symbols, period="5d", interval="1d", progress=True)
        print("\nDownload result:")
        print(data)
        print("\nColumns:", data.columns)
        
        if data.empty:
            print("Data is empty!")
        else:
            print("Data fetched successfully.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_yfinance()
