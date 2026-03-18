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
        "Symbol", "Scrip Name", "ISIN", "Instrument Type", "Quantity Availabl", "Average Price", "Exchange", "Buy Date", "Holder", "Broker"
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
        "symbol": ["Symbol", "symbol", "Scrip Code", "Security Code", "Trading Symbol", "Ticker"],
        "scrip_name": ["Scrip Name", "Scrip", "Instrument Name", "Stock", "Equity", "Security Name"],
        "isin": ["ISIN", "isin", "ISIN Code"],
        "quantity": ["Quantity Availabl", "Quantity Available", "Quantity", "quantity", "Qty", "Shares", "Holdings", "Total Quantity", "Net Quantity", "Net Qty", "Balance", "Balance Quantity", "No. of Shares", "Available Qty", "No. of shares", "Total Shares"],
        "buy_price": ["Average Price", "Buy_Price", "buy_price", "Avg Price", "Cost Price", "Rate", "Average Cost", "Avg Cost", "Buy Price", "Unit Cost", "Price"],
        "exchange": ["Exchange", "exchange", "Market"],
        "holder": ["Holder", "holder", "Investor"],
        "broker": ["Broker", "broker", "Source", "Institution"],
        "buy_date": ["Buy Date", "Buy_Date", "buy_date", "Date", "Purchase Date", "Trade Date"],
        "instrument_type": ["Instrument Type", "Type", "Asset Class", "Instrument"]
    }

    def get_val(row, feature):
        # Case-insensitive column matching
        cols_lower = [c.lower() for c in df.columns]
        for col in mappings.get(feature, []):
            if col.lower() in cols_lower:
                idx = cols_lower.index(col.lower())
                return row[df.columns[idx]]
        return None

    def clean_numeric(val):
        if pd.isna(val) or val is None or str(val).strip() == "":
            return 0
        s = str(val).replace(",", "").replace("₹", "").replace("%", "").replace(" ", "").strip()
        try:
            return float(s)
        except:
            return 0

    preview_data = []
    errors = []
    
    for index, row in df.iterrows():
        try:
            # Flexible identification: Symbol -> ISIN -> Scrip Name
            symbol = get_val(row, "symbol")
            isin = get_val(row, "isin")
            scrip_name_val = get_val(row, "scrip_name")
            
            final_id = None
            if symbol and pd.notna(symbol) and str(symbol).strip() != "":
                final_id = str(symbol).strip()
            elif isin and pd.notna(isin) and str(isin).strip() != "":
                final_id = str(isin).strip()
            elif scrip_name_val and pd.notna(scrip_name_val) and str(scrip_name_val).strip() != "":
                # Fallback: Use scrip name as ID if ticker is missing
                final_id = str(scrip_name_val).strip()
            
            if not final_id:
                # If everything is missing, check if this is an empty row or has data
                qty = clean_numeric(get_val(row, "quantity"))
                if qty <= 0:
                    continue # Valid empty row skip
                # If it has data but no ID, we generate a placeholder or error
                final_id = f"UNKNOWN-{index}"

            # Smart Exchange Identification
            exchange = get_val(row, "exchange")
            if not exchange or pd.isna(exchange):
                # If symbol is numeric, it's almost certainly BSE
                if str(final_id).isdigit():
                    exchange_val = "BSE"
                else:
                    exchange_val = "NSE"
            else:
                exchange_val = str(exchange).upper()
                if exchange_val not in ["NSE", "BSE"]: 
                    # Cross-check for numeric BSE codes mislabeled as NSE
                    if str(final_id).isdigit():
                        exchange_val = "BSE"
                    else:
                        exchange_val = "NSE"

            buy_date_val = get_val(row, "buy_date")
            buy_date = None
            if pd.notna(buy_date_val) and str(buy_date_val).strip() != "":
                try:
                    buy_date = pd.to_datetime(buy_date_val).date()
                except:
                    pass

            item = {
                "exchange": exchange_val,
                "symbol": final_id,
                "quantity": int(clean_numeric(get_val(row, "quantity"))),
                "buy_price": clean_numeric(get_val(row, "buy_price")),
                "buy_date": buy_date,
                "isin": str(isin) if isin and pd.notna(isin) else None,
                "broker": str(get_val(row, "broker")) if pd.notna(get_val(row, "broker")) else "Zerodha",
                "holder": str(get_val(row, "holder")) if pd.notna(get_val(row, "holder")) else None,
                "instrument_type": str(get_val(row, "instrument_type")) if pd.notna(get_val(row, "instrument_type")) else "Stock",
                "scrip_name": str(scrip_name_val) if scrip_name_val and pd.notna(scrip_name_val) else str(final_id)
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
    
    # Calculate Portfolio Units
    from ..services.portfolio_unit_service import calculate_portfolio_nav
    current_status = calculate_portfolio_nav(db, current_user.id)
    nav = current_status["nav"]
    
    # Units = Transaction Value / Current NAV
    transaction_value = equity.buy_price * equity.quantity
    units = transaction_value / nav if nav > 0 else 0
    
    db_equity = Equity(**equity.dict(), user_id=current_user.id, buy_units=units)
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

@router.post("/{equity_id}/sell")
def sell_equity(
    equity_id: int, 
    sell_price: float, 
    sell_date: str,
    quantity: int = None,
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """Mark an equity as sold with sell price and date. Supports partial sales."""
    from datetime import datetime
    from ..models.equity import EquityStatus
    
    equity = db.query(Equity).filter(Equity.id == equity_id, Equity.user_id == current_user.id).first()
    if not equity:
        raise HTTPException(status_code=404, detail="Equity not found")
    
    sell_date_dt = datetime.strptime(sell_date, "%Y-%m-%d").date()

    # Calculate NAV at time of sale
    from ..services.portfolio_unit_service import calculate_portfolio_nav
    current_status = calculate_portfolio_nav(db, current_user.id)
    nav = current_status["nav"]
    
    sell_value = sell_price * (quantity if quantity else equity.quantity)
    units_redeemed = sell_value / nav if nav > 0 else 0

    if quantity is None or quantity >= equity.quantity:
        # Full sale
        equity.status = EquityStatus.SOLD
        equity.sell_price = sell_price
        equity.sell_date = sell_date_dt
        equity.current_price = sell_price
        equity.sell_units = units_redeemed
    else:
        # Partial sale
        if quantity <= 0:
            raise HTTPException(status_code=400, detail="Quantity must be greater than 0")
        
        # Calculate proportional buy units for the sold portion
        fraction = quantity / equity.quantity
        sold_buy_units = equity.buy_units * fraction
        
        # 1. Create a new SOLD record for the partial quantity
        sold_equity = Equity(
            user_id=equity.user_id,
            exchange=equity.exchange,
            symbol=equity.symbol,
            holder=equity.holder,
            quantity=quantity,
            buy_price=equity.buy_price,
            buy_date=equity.buy_date,
            isin=equity.isin,
            broker=equity.broker,
            instrument_type=equity.instrument_type,
            scrip_name=equity.scrip_name,
            status=EquityStatus.SOLD,
            sell_price=sell_price,
            sell_date=sell_date_dt,
            current_price=sell_price, # Lock in valuation
            
            # Unit Logic
            buy_units=sold_buy_units,
            sell_units=units_redeemed
        )
        db.add(sold_equity)
        
        # 2. Subtract quantity AND buy_units from the original ACTIVE record
        equity.quantity -= quantity
        equity.buy_units -= sold_buy_units
        
    db.commit()
    return {"message": "Sale processed successfully", "id": equity_id, "redeemed_units": units_redeemed}


@router.post("/{equity_id}/reactivate")
def reactivate_equity(
    equity_id: int, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """Reactivate a sold equity (undo sell)"""
    from ..models.equity import EquityStatus
    
    equity = db.query(Equity).filter(Equity.id == equity_id, Equity.user_id == current_user.id).first()
    if not equity:
        raise HTTPException(status_code=404, detail="Equity not found")
    
    equity.status = EquityStatus.ACTIVE
    equity.sell_price = None
    equity.sell_date = None
    db.commit()
    db.refresh(equity)
    
    return {"message": "Equity reactivated", "id": equity.id}

@router.get("/")
def get_equities(status: str = "ACTIVE", db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    FAST LOAD: Returns only stored DB values.
    Does NOT fetch live prices. Use /sync-prices for that.
    Filter by status: ACTIVE (default) or SOLD
    """
    from ..models.equity import EquityStatus
    
    query = db.query(Equity).filter(Equity.user_id == current_user.id)
    
    # Filter by status
    if status.upper() == "SOLD":
        query = query.filter(Equity.status == EquityStatus.SOLD)
    elif status.upper() == "ALL":
        pass  # No filter
    else:
        # Default: show only active or NULL status (for backward compatibility)
        query = query.filter((Equity.status == EquityStatus.ACTIVE) | (Equity.status == None))
    
    equities = query.all()
    
    results = []
    for eq in equities:
        eq_dict = {c.name: getattr(eq, c.name) for c in eq.__table__.columns}

        eq_dict = {c.name: getattr(eq, c.name) for c in eq.__table__.columns}
        
        # Use stored price
        current_price = eq.current_price or eq.buy_price or 0.0
        # Use stored prev_close or default to current_price (no change)
        prev_close = eq.prev_close if eq.prev_close is not None else current_price 
        
        eq_dict["current_price"] = current_price
        eq_dict["current_value"] = round(current_price * eq.quantity, 2)
        eq_dict["invested_value"] = round(eq.buy_price * eq.quantity, 2)
        eq_dict["pnl"] = round(eq_dict["current_value"] - eq_dict["invested_value"], 2)
        eq_dict["pnl_percentage"] = round((eq_dict["pnl"] / eq_dict["invested_value"]) * 100, 2) if eq_dict["invested_value"] > 0 else 0
        
        # Daily Gain/Loss (uses stored prev_close)
        daily_change = round(current_price - prev_close, 2)
        eq_dict["daily_change"] = daily_change
        eq_dict["daily_pnl"] = round(daily_change * eq.quantity, 2)
        eq_dict["daily_pnl_percentage"] = round((daily_change / prev_close) * 100, 2) if prev_close > 0 else 0
        
        # Explicitly ensure units are sent
        eq_dict["buy_units"] = eq.buy_units if eq.buy_units is not None else 0.0
        eq_dict["sell_units"] = eq.sell_units if eq.sell_units is not None else 0.0
        
        results.append(eq_dict)
        
    return results

@router.get("/sync-prices")
def sync_equity_prices(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Background Task: Fetches live prices for all equities and updates DB.
    """
    equities = db.query(Equity).filter(Equity.user_id == current_user.id).all()
    
    # Bulk fetch live prices with exchange prefixes
    prefixed_symbols = []
    for eq in equities:
        exc_str = eq.exchange.value if hasattr(eq.exchange, 'value') else str(eq.exchange)
        prefix = "BOM" if exc_str == "BSE" else "NSE"
        prefixed_symbols.append(f"{prefix}:{eq.symbol}")
    
    unique_symbols = list(set(prefixed_symbols))
    from ..services.market_data import fetch_live_stock_prices
    
    # No limit here - we want to sync all (force_refresh=True to bypass cache)
    live_prices = fetch_live_stock_prices(unique_symbols, force_refresh=True)
    
    import logging
    search_count = 0
    updates_made = False
    
    for eq in equities:
        exc_str = eq.exchange.value if hasattr(eq.exchange, 'value') else str(eq.exchange)
        prefix = "BOM" if exc_str == "BSE" else "NSE"
        lookup_key = f"{prefix}:{eq.symbol}"
        price_info = live_prices.get(lookup_key)
        
        if price_info:
            current_price = price_info['price']
            prev_close_val = price_info.get('prev_close', current_price)
            # Update DB
            if current_price > 0:
                eq.current_price = current_price
                eq.prev_close = prev_close_val
                db.add(eq)
                updates_made = True
        else:
            # Fallback Search Logic (Only run if missing)
            if (eq.current_price is None or eq.current_price == 0) and search_count < 5:
                from ..services.market_data import search_ticker_by_name
                search_query = eq.isin or eq.scrip_name
                if search_query:
                    found_ticker = search_ticker_by_name(search_query)
                    if found_ticker:
                        search_count += 1
                        search_prices = fetch_live_stock_prices([found_ticker])
                        if found_ticker in search_prices:
                            current_price = search_prices[found_ticker]['price']
                            prev_close_val = search_prices[found_ticker].get('prev_close', current_price)
                            
                            eq.current_price = current_price
                            eq.prev_close = prev_close_val
                            
                            # Update symbol
                            if len(eq.symbol) > 10 or " " in eq.symbol:
                                 eq.symbol = found_ticker.split('.')[0]
                                 eq.exchange = "BSE" if found_ticker.endswith(".BO") else "NSE"
                            db.add(eq)
                            updates_made = True
                            
    if updates_made:
        db.commit()
        
    return {"status": "synced"}

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
