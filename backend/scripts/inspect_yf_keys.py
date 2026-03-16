import yfinance as yf
import pandas as pd
import json

def inspect_ticker(symbol):
    print(f"--- Inspecting {symbol} ---")
    ticker = yf.Ticker(symbol)
    
    try:
        is_stmt = ticker.income_stmt
        bs_stmt = ticker.balance_sheet
        
        info = {
            "symbol": symbol,
            "income_stmt_keys": is_stmt.index.tolist(),
            "balance_sheet_keys": bs_stmt.index.tolist(),
            "years": is_stmt.columns.strftime('%Y-%m-%d').tolist() if not is_stmt.empty else []
        }
        
        # Check specific required fields
        required_income = ["Net Income", "EBIT", "Operating Income"]
        required_balance = ["Stockholders Equity", "Total Assets", "Total Current Liabilities", "Current Liabilities"]
        
        found_income = [k for k in required_income if k in is_stmt.index]
        found_balance = [k for k in required_balance if k in bs_stmt.index]
        
        print(f"Found Income Keys: {found_income}")
        print(f"Found Balance Keys: {found_balance}")
        
    except Exception as e:
        print(f"Error inspecting {symbol}: {e}")

inspect_ticker("HDFCBANK.NS")
inspect_ticker("RELIANCE.NS")
inspect_ticker("TCS.NS")
