import yfinance as yf
import pandas as pd
from datetime import datetime

def check():
    symbols = ["^NSEI", "^BSESN"]
    print(f"Current Time: {datetime.now()}")
    for sym in symbols:
        print(f"\n--- {sym} ---")
        t = yf.Ticker(sym)
        
        # Test 1d, 1m
        print("Fetching 1d, 1m...")
        df_1m = t.history(period="1d", interval="1m")
        if not df_1m.empty:
            print(f"Latest 1m Close: {df_1m['Close'].iloc[-1]} at {df_1m.index[-1]}")
            print(f"1m Datapoints: {len(df_1m)}")
        else:
            print("1m Data Empty")
            
        # Test 2d, 1d
        print("Fetching 2d, 1d...")
        df_2d = t.history(period="2d", interval="1d")
        if not df_2d.empty:
            print("2d History:")
            print(df_2d['Close'])
            if len(df_2d) >= 2:
                print(f"Previous Close (iloc[-2]): {df_2d['Close'].iloc[-2]}")
        else:
            print("2d Data Empty")

if __name__ == "__main__":
    check()
