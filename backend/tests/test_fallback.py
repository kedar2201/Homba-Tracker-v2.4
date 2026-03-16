import yfinance as yf
import pandas as pd

ticker = "NEWGEN.NS"
t = yf.Ticker(ticker)

print(f"--- Fetching for {ticker} ---")
info = t.info
print(f"Info ROE: {info.get('returnOnEquity')}")

try:
    income = t.income_stmt
    balance = t.balance_sheet
    
    if not income.empty:
        print("\nIncome Statement (Keys):")
        print(income.index.tolist())
        net_inc = income.iloc[:, 0].get('Net Income')
        print(f"Latest Net Income: {net_inc}")
        
    if not balance.empty:
        print("\nBalance Sheet (Keys):")
        print(balance.index.tolist())
        equity = (balance.iloc[:, 0].get('Stockholders Equity') 
                 or balance.iloc[:, 0].get('Common Stock Equity')
                 or balance.iloc[:, 0].get('Total Equity Gross Minority Interest'))
        print(f"Latest Equity: {equity}")
        
        assets = balance.iloc[:, 0].get('Total Assets')
        liab = balance.iloc[:, 0].get('Current Liabilities')
        print(f"Assets: {assets}, Curr Liab: {liab}")
        
        if net_inc and equity:
            computed_roe = (net_inc / equity) * 100
            print(f"\nCOMPUTED ROE: {computed_roe}%")

except Exception as e:
    print(f"Error: {e}")
