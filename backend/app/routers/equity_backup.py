from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from typing import List
import pandas as pd
import io
from ..database import get_db
from ..models.equity import Equity
from ..schemas.equity import EquityCreate, EquitySchema, Exchange
from ..models.user import User
from ..services.calculations import get_equity_current_value, MOCK_EQUITY_PRICES
from ..services.market_data import fetch_live_stock_prices
from ..auth.auth import get_current_user

router = APIRouter(
    tags=["Equity"],
)

@router.get("/template")
def get_equity_template():
    df = pd.DataFrame(columns=[
        "Symbol", "ISIN", "Instrument Type", "Quantity Availabl", "Quantity Discrepa", "Quantity Pledged", "Average Price", "Previous Closing P", "Unrealized P&L", "Unrealized P&L Pe",
        "Exchange", "Buy Date", "Holder", "Broker"
    ])
    stream = io.StringIO()
    df.to_csv(stream, index=False)
    response = stream.getvalue()
    from fastapi.responses import Response
    return Response(content=response, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=equity_template.csv"})

@router.post("/preview-upload")
async def preview_equity_upload(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    contents = await file.read()
    if file.filename.endswith('.csv'):
        df = pd.read_csv(io.BytesIO(contents))
    elif file.filename.endswith(('.xls', '.xlsx')):
        df = pd.read_excel(io.BytesIO(contents))
    else:
        raise HTTPException(status_code=400, detail="Invalid file format")

    # Define possible column mappings
    mappings = {
        "symbol": ["Symbol", "symbol"],
        "isin": ["ISIN", "isin"],
        "quantity": ["Quantity Availabl", "Quantity Available", "Quantity", "quantity", "Qty"],
        "buy_price": ["Average Price", "Buy_Price", "buy_price", "Avg Price"],
        "exchange": ["Exchange", "exchange"],
        "holder": ["Holder", "holder"],
        "broker": ["Broker", "broker", "Source"],
        "buy_date": ["Buy Date", "Buy_Date", "buy_date", "Date"]
    }

    def get_val(row, feature):
        for col in mappings.get(feature, []):
            if col in df.columns:
                return row[col]
        return None

    def clean_numeric(val):
        if pd.isna(val) or val is None or str(val).strip() == "":
            return 0
        s = str(val).replace(",", "").replace("₹", "").replace("%", "").strip()
        try:
            return float(s)
        except:
            return 0

    preview_data = []
    errors = []
    
    for index, row in df.iterrows():
        try:
            symbol = get_val(row, "symbol")
            if not symbol or pd.isna(symbol): continue # Skip empty rows

            exchange = get_val(row, "exchange")
            if not exchange or pd.isna(exchange):
                exchange_val = "NSE"
            else:
                exchange_val = str(exchange).upper()
                if exchange_val not in ["NSE", "BSE"]: exchange_val = "NSE"

            buy_date_val = get_val(row, "buy_date")
            buy_date = None
            if pd.notna(buy_date_val) and str(buy_date_val).strip() != "":
                try:
                    buy_date = pd.to_datetime(buy_date_val).date()
                except:
                    pass

            item = {
                "exchange": exchange_val,
                "symbol": str(symbol),
                "quantity": int(clean_numeric(get_val(row, "quantity"))),
                "buy_price": clean_numeric(get_val(row, "buy_price")),
                "buy_date": buy_date,
                "isin": str(get_val(row, "isin")) if pd.notna(get_val(row, "isin")) else None,
                "broker": str(get_val(row, "broker")) if pd.notna(get_val(row, "broker")) else "Zerodha",
                "holder": str(get_val(row, "holder")) if pd.notna(get_val(row, "holder")) else None
            }
            validated = EquityCreate(**item)
            preview_data.append(validated.dict())
        except Exception as e:
            errors.append({"row": index + 2, "error": str(e)})

    return {"preview": preview_data, "errors": errors, "total_rows": len(df)}

@router.post("/confirm-upload", response_model=List[EquitySchema])
def confirm_equity_upload(data: List[EquityCreate], db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    items = []
    for item in data:
        db_item = Equity(**item.dict(), user_id=current_user.id)
        db.add(db_item)
        items.append(db_item)
    db.commit()
    for i in items:
        db.refresh(i)
    return items

@router.post("/", response_model=EquitySchema)
def create_equity(equity: EquityCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_equity = Equity(**equity.dict(), user_id=current_user.id)
    db.add(db_equity)
    db.commit()
    db.refresh(db_equity)
    return db_equity

@router.delete("/{equity_id}", status_code=204)
def delete_equity(equity_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    equity = db.query(Equity).filter(Equity.id == equity_id, Equity.user_id == current_user.id).first()
    if not equity:
        raise HTTPException(status_code=404, detail="Equity not found")
    db.delete(equity)
    db.commit()
    return None

@router.get("/")
def get_equities(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    equities = db.query(Equity).filter(Equity.user_id == current_user.id).all()
    
    # Bulk fetch live prices with exchange prefixes
    prefixed_symbols = []
    for eq in equities:
        # Use .value if it's an enum, or handle if it's already a string
        exc_str = eq.exchange.value if hasattr(eq.exchange, 'value') else str(eq.exchange)
        prefix = "BOM" if exc_str == "BSE" else "NSE"
        prefixed_symbols.append(f"{prefix}:{eq.symbol}")
        
    symbol_list = list(set(prefixed_symbols))
    live_prices = fetch_live_stock_prices(symbol_list)
    import logging
    logging.info(f"Live Price Fetch ({len(symbol_list)} symbols): {symbol_list[:5]}...")
    
    results = []
    for eq in equities:
        eq_dict = {c.name: getattr(eq, c.name) for c in eq.__table__.columns}
        # Get market price info using prefixed key
        exc_str = eq.exchange.value if hasattr(eq.exchange, 'value') else str(eq.exchange)
        prefix = "BOM" if exc_str == "BSE" else "NSE"
        lookup_key = f"{prefix}:{eq.symbol}"
        price_info = live_prices.get(lookup_key)
        
        if price_info:
            current_price = price_info['price']
            prev_close = price_info['prev_close']
        else:
            # Fallback priority: Stored current_price -> buy_price -> 0
            current_price = eq.current_price or eq.buy_price or 0.0
            prev_close = current_price
            
        # Update the DB model with latest price if we got a real one
        if price_info and current_price > 0:
            eq.current_price = current_price
            db.add(eq)
            
        eq_dict["current_price"] = current_price
        eq_dict["current_value"] = round(current_price * eq.quantity, 2)
        eq_dict["invested_value"] = round(eq.buy_price * eq.quantity, 2)
        eq_dict["pnl"] = round(eq_dict["current_value"] - eq_dict["invested_value"], 2)
        eq_dict["pnl_percentage"] = round((eq_dict["pnl"] / eq_dict["invested_value"]) * 100, 2) if eq_dict["invested_value"] > 0 else 0
        
        # Daily Gain/Loss
        eq_dict["daily_change"] = round(current_price - prev_close, 2)
        eq_dict["daily_pnl"] = round(eq_dict["daily_change"] * eq.quantity, 2)
        eq_dict["daily_pnl_percentage"] = round((eq_dict["daily_change"] / prev_close) * 100, 2) if prev_close > 0 else 0
        
        results.append(eq_dict)
    
    db.commit() # Save updated current_price values
    return results

@router.put("/{equity_id}", response_model=EquitySchema)
def update_equity(equity_id: int, equity_data: EquityCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_equity = db.query(Equity).filter(Equity.id == equity_id, Equity.user_id == current_user.id).first()
    if not db_equity:
        raise HTTPException(status_code=404, detail="Equity not found")
    
    for key, value in equity_data.dict().items():
        setattr(db_equity, key, value)
    
    db.commit()
    db.refresh(db_equity)
    return db_equity
