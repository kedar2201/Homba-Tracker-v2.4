from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from typing import List
import pandas as pd
import io
from ..database import get_db
from ..models.mutual_fund import MutualFund
from ..schemas.mutual_fund import MFCreate, MFSchema
from ..models.user import User
from ..services.calculations import get_mf_current_value, MOCK_MF_NAVS
from ..auth.auth import get_current_user

router = APIRouter(
    tags=["Mutual Funds"],
)

@router.get("/template")
def get_mf_template():
    df = pd.DataFrame(columns=[
        "Scheme Name", "ISIN", "Units", "Invested Amount", "Transaction Date", "AMC Name", "AMFI Code", "Holder", "Depositor Name", "Depositor Code"
    ])
    stream = io.StringIO()
    df.to_csv(stream, index=False)
    response = stream.getvalue()
    from fastapi.responses import Response
    return Response(content=response, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=mf_template.csv"})

@router.post("/preview-upload")
async def preview_mf_upload(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    try:
        contents = await file.read()
        if file.filename.lower().endswith('.csv'):
            try:
                df = pd.read_csv(io.BytesIO(contents))
            except UnicodeDecodeError:
                # Fallback for Excel-saved CSVs on Windows
                df = pd.read_csv(io.BytesIO(contents), encoding='cp1252')
        elif file.filename.lower().endswith(('.xls', '.xlsx')):
            df = pd.read_excel(io.BytesIO(contents))
        else:
            raise HTTPException(status_code=400, detail="Invalid format. Please upload a CSV or Excel file.")
    except Exception as e:
        import logging
        logging.error(f"Error reading file {file.filename}: {e}")
        raise HTTPException(status_code=400, detail=f"Could not read file: {str(e)}")

    # Define possible column mappings
    mappings = {
        "scheme_name": ["Scheme Name", "Scheme_Name", "scheme_name", "Scheme"],
        "units": ["Units", "units", "Quantity", "Qty"],
        # "Invested Amount" -> Total Value (Mandatory)
        "invested_amount_total": ["Invested Amount", "Invested_Amount", "Total Cost", "Total Amount", "Investment Cost", "Investment_Cost", "Cost", "Avg. Cost"],
        # "Unit Price" -> Price per Unit (Optional fallback)
        "unit_price": ["NAV", "Unit Price", "Price", "Average Price"],
        "isin": ["ISIN", "isin"],
        "transaction_date": ["Transaction Date", "Transaction_Date", "Date"],
        "holder": ["Holder", "holder"],
        "amc_name": ["AMC Name", "AMC_Name"],
        "amfi_code": ["AMFI Code", "AMFI_Code"],
        "depositor_name": ["Depositor Name", "Depositor_Name"],
        "depositor_code": ["Depositor Code", "Depositor_Code"]
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
            scheme_name = get_val(row, "scheme_name")
            if not scheme_name or pd.isna(scheme_name): continue

            tx_date_val = get_val(row, "transaction_date")
            tx_date = None
            if pd.notna(tx_date_val) and str(tx_date_val).strip() != "":
                try:
                    tx_date = pd.to_datetime(tx_date_val).date()
                except:
                    pass
            
            units = clean_numeric(get_val(row, "units"))
            
            # Smart Amount Calculation
            total_amount = clean_numeric(get_val(row, "invested_amount_total"))
            unit_price = clean_numeric(get_val(row, "unit_price"))
            
            final_invested_amount = 0.0
            
            if total_amount > 0:
                final_invested_amount = total_amount
            elif unit_price > 0 and units > 0:
                # User provided Cost Per Unit (e.g. 13.36) -> Calculate Total
                final_invested_amount = units * unit_price
            else:
                # Fallback: if we only interpret "Investment Cost" as total because it was mapped there before?
                # No, strict separation now.
                 final_invested_amount = 0.0

            item = {
                "scheme_name": str(scheme_name),
                "depositor_name": str(get_val(row, "depositor_name")) if pd.notna(get_val(row, "depositor_name")) else None,
                "depositor_code": str(get_val(row, "depositor_code")) if pd.notna(get_val(row, "depositor_code")) else None,
                "isin": str(get_val(row, "isin")) if pd.notna(get_val(row, "isin")) else None,
                "units": units,
                "invested_amount": round(final_invested_amount, 2),
                "transaction_date": tx_date,
                "holder": str(get_val(row, "holder")) if pd.notna(get_val(row, "holder")) else None,
                "amc_name": str(get_val(row, "amc_name")) if pd.notna(get_val(row, "amc_name")) else None,
                "amfi_code": str(get_val(row, "amfi_code")) if pd.notna(get_val(row, "amfi_code")) else None
            }
            validated = MFCreate(**item)
            preview_data.append(validated.dict())
        except Exception as e:
            errors.append({"row": index + 2, "error": str(e)})

    return {"preview": preview_data, "errors": errors, "total_rows": len(df)}

@router.post("/confirm-upload", response_model=List[MFSchema])
def confirm_mf_upload(data: List[MFCreate], db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    new_mfs = []
    
    # Pre-fetch existing to avoid N+1 queries if possible, but for safety lets check one by one or optimized
    # For now, simple check is fine for typical batch sizes < 100
    
    for item in data:
        # Check for duplicates
        exists = db.query(MutualFund).filter(
            MutualFund.user_id == current_user.id,
            MutualFund.scheme_name == item.scheme_name,
            MutualFund.units == item.units,
            MutualFund.invested_amount == item.invested_amount,
            MutualFund.transaction_date == item.transaction_date
        ).first()
        
        if not exists:
            db_mf = MutualFund(**item.dict(), user_id=current_user.id)
            db.add(db_mf)
            new_mfs.append(db_mf)
            
    if new_mfs:
        db.commit()
        for mf in new_mfs:
            db.refresh(mf)
            
    return new_mfs

@router.post("/", response_model=MFSchema)
def create_mutual_fund(mf: MFCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    
    # Calculate Portfolio Units
    from ..services.portfolio_unit_service import calculate_portfolio_nav
    current_status = calculate_portfolio_nav(db, current_user.id)
    nav = current_status["nav"]
    
    # Calculate Invested Amount (if not provided, derive from units * nav? No, input has it)
    # Unit Logic: P_Buy_Units = Invested Amount / Portfolio NAV
    invested = mf.invested_amount
    p_units = invested / nav if nav > 0 else 0
    
    db_mf = MutualFund(**mf.dict(), user_id=current_user.id, p_buy_units=p_units)
    db.add(db_mf)
    db.commit()
    db.refresh(db_mf)
    return db_mf

@router.delete("/{mf_id}", status_code=204)
def delete_mutual_fund(mf_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    mf = db.query(MutualFund).filter(MutualFund.id == mf_id, MutualFund.user_id == current_user.id).first()
    if not mf:
        raise HTTPException(status_code=404, detail="Mutual Fund not found")
    db.delete(mf)
    db.commit()
    return None

@router.post("/{mf_id}/sell")
def sell_mutual_fund(
    mf_id: int, 
    sell_nav: float, 
    sell_date: str,
    units: float = None,
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """Mark a mutual fund as sold with sell NAV and date. Supports partial sales."""
    from datetime import datetime
    from ..models.mutual_fund import MFStatus
    
    mf = db.query(MutualFund).filter(MutualFund.id == mf_id, MutualFund.user_id == current_user.id).first()
    if not mf:
        raise HTTPException(status_code=404, detail="Mutual Fund not found")
    
    sell_date_dt = datetime.strptime(sell_date, "%Y-%m-%d").date()

    sell_date_dt = datetime.strptime(sell_date, "%Y-%m-%d").date()

    # Calculate NAV at time of sale
    from ..services.portfolio_unit_service import calculate_portfolio_nav
    current_status = calculate_portfolio_nav(db, current_user.id)
    portfolio_nav = current_status["nav"]
    
    # Calculate Value of Sale
    # Units to sell * Sell NAV
    units_to_sell = units if units else mf.units
    sell_value = units_to_sell * sell_nav
    
    portfolio_units_redeemed = sell_value / portfolio_nav if portfolio_nav > 0 else 0

    if units is None or units >= mf.units:
        # Full sale
        mf.status = MFStatus.SOLD
        mf.sell_nav = sell_nav
        mf.sell_date = sell_date_dt
        mf.p_sell_units = portfolio_units_redeemed
    else:
        # Partial sale
        if units <= 0:
            raise HTTPException(status_code=400, detail="Units must be greater than 0")
            
        # Calculate proportional invested amount for the sold part
        fraction = units / mf.units
        proportional_invested = mf.invested_amount * fraction
        proportional_p_buy_units = mf.p_buy_units * fraction
        
        # 1. Create a new SOLD record for the partial units
        sold_mf = MutualFund(
            user_id=mf.user_id,
            scheme_name=mf.scheme_name,
            depositor_name=mf.depositor_name,
            depositor_code=mf.depositor_code,
            holder=mf.holder,
            isin=mf.isin,
            units=units,
            invested_amount=round(proportional_invested, 2),
            transaction_date=mf.transaction_date,
            amc_name=mf.amc_name,
            amfi_code=mf.amfi_code,
            interest_rate=mf.interest_rate,
            status=MFStatus.SOLD,
            sell_nav=sell_nav,
            sell_date=sell_date_dt,
            
            # Unit Logic
            p_buy_units=proportional_p_buy_units,
            p_sell_units=portfolio_units_redeemed
        )
        db.add(sold_mf)
        
        # 2. Subtract units, proportional invested amount, and p_buy_units from the original ACTIVE record
        mf.units -= units
        mf.invested_amount = round(mf.invested_amount - proportional_invested, 2)
        mf.p_buy_units -= proportional_p_buy_units
        
    db.commit()
    return {"message": "Sale processed successfully", "id": mf_id, "redeemed_units": portfolio_units_redeemed}


@router.post("/{mf_id}/reactivate")
def reactivate_mutual_fund(
    mf_id: int, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """Reactivate a sold mutual fund (undo sell)"""
    from ..models.mutual_fund import MFStatus
    
    mf = db.query(MutualFund).filter(MutualFund.id == mf_id, MutualFund.user_id == current_user.id).first()
    if not mf:
        raise HTTPException(status_code=404, detail="Mutual Fund not found")
    
    mf.status = MFStatus.ACTIVE
    mf.sell_nav = None
    mf.sell_date = None
    db.commit()
    db.refresh(mf)
    
    return {"message": "Mutual Fund reactivated", "id": mf.id}

@router.get("/")
def get_mfs(status: str = "ACTIVE", db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Get mutual funds with status filtering.
    status: ACTIVE (default), SOLD, or ALL
    """
    from ..models.mutual_fund import MFStatus
    
    query = db.query(MutualFund).filter(MutualFund.user_id == current_user.id)
    
    if status.upper() == "SOLD":
        query = query.filter(MutualFund.status == MFStatus.SOLD)
    elif status.upper() == "ALL":
        pass
    else:
        # Default ACTIVE
        query = query.filter((MutualFund.status == MFStatus.ACTIVE) | (MutualFund.status == None))
        
    mfs = query.all()
    
    unique_amfi_codes = list(set(mf.amfi_code for mf in mfs if mf.amfi_code))
    from ..services.market_data import fetch_mf_nav, search_mf_nav_by_name
    from concurrent.futures import ThreadPoolExecutor
    
    # Process AMFI codes in bulk
    with ThreadPoolExecutor(max_workers=10) as executor:
        nav_results = list(executor.map(fetch_mf_nav, unique_amfi_codes))
        
    nav_map = dict(zip(unique_amfi_codes, nav_results))
    
    results = []
    from ..services.calculations import get_sgb_current_value, MOCK_GOLD_PRICE
    
    for mf in mfs:
        mf_dict = {c.name: getattr(mf, c.name) for c in mf.__table__.columns}
        
        # SGB Case
        if mf.interest_rate and mf.interest_rate > 0:
            mf_dict["current_nav"] = MOCK_GOLD_PRICE
            mf_dict["current_value"] = get_sgb_current_value(mf.units)
        else:
            nav = None
            
            # Try AMFI Code or ISIN first (uses official AMFI cache)
            if mf.amfi_code or mf.isin:
                nav = fetch_mf_nav(amfi_code=mf.amfi_code, isin=mf.isin)
                
            # Fallback to search by name if no nav found yet
            if nav is None:
                search_result = search_mf_nav_by_name(mf.scheme_name)
                if search_result:
                    # Handle new dict return type or legacy float
                    if isinstance(search_result, dict):
                        nav = search_result.get('nav')
                        # The self-healing logic block was removed here
                    else:
                        nav = search_result
                
            if nav is None:
                nav = MOCK_MF_NAVS.get(mf.isin, 50.0)
                
            mf_dict["current_nav"] = nav
            mf_dict["current_value"] = round(nav * mf.units, 2)
        
        mf_dict["pnl"] = round(mf_dict["current_value"] - mf.invested_amount, 2)
        mf_dict["pnl_percentage"] = round((mf_dict["pnl"] / mf.invested_amount) * 100, 2) if mf.invested_amount > 0 else 0
        
        # Explicitly ensure portfolio units are sent
        mf_dict["p_buy_units"] = mf.p_buy_units if mf.p_buy_units is not None else 0.0
        mf_dict["p_sell_units"] = mf.p_sell_units if mf.p_sell_units is not None else 0.0
        
        results.append(mf_dict)
    return results

@router.put("/{mf_id}", response_model=MFSchema)
def update_mutual_fund(mf_id: int, mf_data: MFCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_mf = db.query(MutualFund).filter(MutualFund.id == mf_id, MutualFund.user_id == current_user.id).first()
    if not db_mf:
        raise HTTPException(status_code=404, detail="Mutual Fund not found")
    
    for key, value in mf_data.dict(exclude_unset=True).items():
        setattr(db_mf, key, value)
    
    db.commit()
    db.refresh(db_mf)
    return db_mf
