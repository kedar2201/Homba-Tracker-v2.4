import yfinance as yf
import pandas as pd
import logging
from typing import Dict

def _fetch_single_test(yf_ticker: str):
    t = yf.Ticker(yf_ticker)
    print(f"Testing {yf_ticker}...")
    
    if str(yf_ticker).startswith("^"):
        try:
            live_data = t.history(period="1d", interval="1m")
            if not live_data.empty:
                current_price = float(live_data['Close'].iloc[-1])
                print(f"  Live (1m) Price: {current_price} at {live_data.index[-1]}")
                
                hist_2d = t.history(period="2d", interval="1d")
                prev_close = current_price
                if len(hist_2d) >= 2:
                    prev_close = float(hist_2d['Close'].iloc[-2])
                    print(f"  Prev Close (2d): {prev_close}")
                elif hasattr(t, 'fast_info'):
                    try:
                        fi = t.fast_info
                        prev_close = fi.get('previous_close', fi.get('previousClose', current_price))
                        print(f"  Prev Close (FastInfo): {prev_close}")
                    except: pass
                
                return {
                    'price': round(current_price, 2),
                    'prev_close': round(prev_close, 2)
                }
            else:
                print("  Live (1m) Data Empty")
        except Exception as index_e:
            print(f"  Error in 1m fetch: {index_e}")

    # Old logic
    hist = t.history(period="2d")
    if not hist.empty:
        current_price = float(hist['Close'].iloc[-1])
        prev_close = float(hist['Close'].iloc[-2]) if len(hist) >= 2 else current_price
        print(f"  History (2d) Price: {current_price}, Prev: {prev_close}")
        return {
            'price': round(current_price, 2),
            'prev_close': round(prev_close, 2)
        }
    else:
        print("  History (2d) Data Empty")
    
    return None

if __name__ == "__main__":
    for sym in ["^NSEI", "^BSESN"]:
        res = _fetch_single_test(sym)
        print(f"  Result: {res}")
        print("-" * 20)
