from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
import pandas as pd
import io
from ..database import get_db
from ..models.fixed_deposit import FixedDeposit
from ..schemas.fixed_deposit import FDCreate, FDSchema, CompoundingFrequency, PayoutType
from ..models.user import User
from ..services.calculations import calculate_fd_maturity
from ..auth.auth import get_current_user

router = APIRouter(
    tags=["Fixed Deposits"],
)

@router.get("/template")
def get_fd_template():
    # Generate a CSV with headers
    df = pd.DataFrame(columns=[
        "Bank Name", "FD Code", "Principal", "Interest Rate", "Start Date", "Maturity Date", "Compounding Frequency", "Payout Type", "TDS Applicable", "TDS Rate", "Depositor Name", "Depositor Code"
    ])
    stream = io.StringIO()
    df.to_csv(stream, index=False)
    response = stream.getvalue()
    from fastapi.responses import Response
    return Response(content=response, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=fd_template.csv"})

@router.post("/preview-upload")
async def preview_fd_upload(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    # Read file
    contents = await file.read()
    if file.filename.endswith('.csv'):
        df = pd.read_csv(io.BytesIO(contents))
    elif file.filename.endswith(('.xls', '.xlsx')):
        df = pd.read_excel(io.BytesIO(contents))
    else:
        raise HTTPException(status_code=400, detail="Invalid file format")

    # Define possible column mappings (normalized to lowercase)
    mappings = {
        "bank_name": ["bank name", "bank_name", "bank", "institution"],
        "fd_code": ["fd code", "fd_code", "account number", "account_no", "fd no", "certificate no"],
        "principal": ["principal", "amount", "deposit amount", "invested", "face value", "sum assured", "investment"],
        "interest_rate": ["interest rate", "interest_rate", "rate", "roi"],
        "start_date": ["start date", "start_date", "date of booking", "booking date"],
        "maturity_date": ["maturity date", "maturity_date"],
        "compounding_frequency": ["compounding frequency", "compounding_frequency"],
        "payout_type": ["payout type", "payout_type"],
        "depositor_name": ["depositor name", "depositor_name", "name", "holder"],
        "depositor_code": ["depositor code", "depositor_code", "investor code", "code"],
        "tds_applicable": ["tds applicable", "tds_applicable"],
        "tds_rate": ["tds rate", "tds_rate"]
    }

    # Normalize column names for easier matching
    df.columns = [str(c).strip().lower() for c in df.columns]

    def get_val(row, feature):
        best_val = None
        for col in mappings.get(feature, []):
            if col in df.columns:
                val = row[col]
                # For principal/rate, if we find a 0, we can keep looking
                if feature in ["principal", "interest_rate"]:
                    clean = clean_numeric(val)
                    if clean > 0:
                        return val
                    if best_val is None:
                        best_val = val
                else:
                    return val
        return best_val

    def clean_numeric(val):
        if pd.isna(val) or val is None or str(val).strip() == "":
            return 0
        s = str(val).lower()
        # Remove currency symbols and common text
        for pat in [",", "₹", "%", "rs.", "rs", "/-", "usd"]:
            s = s.replace(pat, "")
        s = s.strip()
        try:
            return float(s)
        except:
            # Try to extract numbers from string
            import re
            nums = re.findall(r"[-+]?\d*\.\d+|\d+", s)
            if nums: return float(nums[0])
            return 0

    # Parse and Validate Rows
    preview_data = []
    errors = []
    
    for index, row in df.iterrows():
        try:
            bank_name = get_val(row, "bank_name")
            if not bank_name or pd.isna(bank_name): continue

            start_date_val = get_val(row, "start_date")
            start_date = None
            if pd.notna(start_date_val) and str(start_date_val).strip() != "":
                try:
                    start_date = pd.to_datetime(start_date_val).date()
                except:
                    pass

            maturity_date_val = get_val(row, "maturity_date")
            maturity_date = None
            if pd.notna(maturity_date_val) and str(maturity_date_val).strip() != "":
                try:
                    maturity_date = pd.to_datetime(maturity_date_val).date()
                except:
                    pass

            # Short form mapping for Compounding and Payout
            freq_raw = str(get_val(row, "compounding_frequency") or "Yearly").strip().upper()
            payout_raw = str(get_val(row, "payout_type") or "Cumulative").strip().upper()
            
            FREQ_MAP = {
                "M": "Monthly", "Q": "Quarterly", "HYP": "Half-Yearly", 
                "AIP": "Yearly", "Y": "Yearly", "ANN": "Yearly",
                "MAT": "On Maturity"
            }
            PAY_MAP = {
                "M": "Monthly Payout", "Q": "Quarterly Payout", "HYP": "Half-Yearly Payout",
                "AIP": "Annual Payout", "C": "Cumulative", "CUM": "Cumulative",
                "ANNUAL": "Annual Payout"
            }

            final_freq = FREQ_MAP.get(freq_raw, get_val(row, "compounding_frequency") or "Yearly")
            final_payout = PAY_MAP.get(payout_raw, get_val(row, "payout_type") or "Cumulative")

            # Generate a truly unique fd_code for this user during import
            raw_fd_code = str(get_val(row, "fd_code") or "").strip()
            if not raw_fd_code or raw_fd_code.lower() == "nan":
                unique_fd_code = f"FD-GEN-{index}"
            else:
                # If the same code appears multiple times in the file, distinguish them
                # (to prevent them from overwriting each other in the same import)
                unique_fd_code = raw_fd_code
                if df[df.columns[df.columns.tolist().index(mappings['fd_code'][0]) if mappings['fd_code'][0] in df.columns else 0]].tolist().count(raw_fd_code) > 1:
                     # This is a bit slow but safe for 100-200 rows
                     # Find how many times this code has appeared BEFORE this row
                     # Actually simpler: just append row index to ALWAYS be safe if there's any ambiguity
                     pass

            # Simpler approach: Include row index in fallback or if duplicates suspected
            # But wait, if they really are the SAME FD, we might want to sum them? 
            # No, user usually wants them as separate line items if they are separate rows.
            
            # Revised logic:
            final_fd_code = raw_fd_code if raw_fd_code and raw_fd_code.lower() != "nan" else f"TEMP-{index}"
            # To avoid collision with existing records if the code is generic, 
            # we can't easily change it here without breaking the 'update' logic.
            # But the user said "total is wrong". 
            # If 108 rows -> 71 saved, it's definitely overwrites.
            
            item = {
                "bank_name": str(bank_name),
                "depositor_name": str(get_val(row, "depositor_name")) if pd.notna(get_val(row, "depositor_name")) else None,
                "depositor_code": str(get_val(row, "depositor_code")) if pd.notna(get_val(row, "depositor_code")) else None,
                "fd_code": final_fd_code,
                "principal": clean_numeric(get_val(row, "principal")),
                "interest_rate": clean_numeric(get_val(row, "interest_rate")),
                "start_date": start_date,
                "maturity_date": maturity_date,
                "compounding_frequency": final_freq,
                "payout_type": final_payout,
                "tds_applicable": bool(get_val(row, "tds_applicable") if get_val(row, "tds_applicable") is not None else False),
                "tds_rate": clean_numeric(get_val(row, "tds_rate"))
            }
            # Handle rate if expressed as decimal (e.g. 0.07 instead of 7)
            if 0 < item["interest_rate"] < 1: item["interest_rate"] *= 100
            
            validated = FDCreate(**item)
            preview_data.append(validated.dict())
        except Exception as e:
            errors.append({"row": index + 2, "error": str(e)})

    return {"preview": preview_data, "errors": errors, "total_rows": len(df)}

@router.post("/confirm-upload", response_model=List[FDSchema])
def confirm_fd_upload(data: List[FDCreate], db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    results = []
    # Track codes processed in THIS batch to handle duplicates within the file
    processed_codes = {} 
    
    for item in data:
        code = item.fd_code
        # How many times have we seen this code in this specific upload?
        count = processed_codes.get(code, 0)
        suffix = f"-{count}" if count > 0 else ""
        unique_batch_code = f"{code}{suffix}"
        
        # Check if this specific unique combination already exists for this user
        existing = db.query(FixedDeposit).filter(
            FixedDeposit.fd_code == unique_batch_code, 
            FixedDeposit.user_id == current_user.id
        ).first()
        
        if existing:
            # Update existing
            for key, value in item.dict().items():
                if key != "fd_code": # Don't update the code keep suffix
                    setattr(existing, key, value)
            results.append(existing)
        else:
            # Create new
            final_item_dict = item.dict()
            final_item_dict["fd_code"] = unique_batch_code
            db_fd = FixedDeposit(**final_item_dict, user_id=current_user.id)
            db.add(db_fd)
            results.append(db_fd)
        
        processed_codes[code] = count + 1
        db.flush()
    
    db.commit()
    for fd in results:
        db.refresh(fd)
    return results

@router.post("/", response_model=FDSchema)
def create_fd(item: FDCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_fd = FixedDeposit(**item.dict(), user_id=current_user.id)
    db.add(db_fd)
    db.commit()
    db.refresh(db_fd)
    return db_fd

@router.get("/")
def get_fds(fy_year: Optional[int] = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    fds = db.query(FixedDeposit).filter(FixedDeposit.user_id == current_user.id).all()
    
    from ..services.calculations import calculate_fd_interest_for_fy
    
    results = []
    for fd in fds:
        fd_dict = {c.name: getattr(fd, c.name) for c in fd.__table__.columns}
        
        # Consistently use Yearly if frequency is null
        freq = fd.compounding_frequency.value if (fd.compounding_frequency and hasattr(fd.compounding_frequency, 'value')) else "Yearly"
        
        fd_dict["maturity_value"] = calculate_fd_maturity(
            fd.principal, 
            fd.interest_rate, 
            fd.start_date, 
            fd.maturity_date, 
            freq
        )
        
        # FY Interest Calculation
        if fy_year:
            fd_dict["fy_interest"] = calculate_fd_interest_for_fy(
                fd.principal,
                fd.interest_rate,
                fd.start_date,
                fd.maturity_date,
                freq,
                fy_year
            )
        else:
            fd_dict["fy_interest"] = 0.0
            
        results.append(fd_dict)
    return results
@router.delete("/{fd_id}")
def delete_fd(fd_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    fd = db.query(FixedDeposit).filter(FixedDeposit.id == fd_id, FixedDeposit.user_id == current_user.id).first()
    if not fd:
        raise HTTPException(status_code=404, detail="Fixed Deposit not found")
    db.delete(fd)
    db.commit()
    return {"message": "Fixed Deposit deleted successfully"}

@router.put("/{fd_id}", response_model=FDSchema)
def update_fd(fd_id: int, item: FDCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_fd = db.query(FixedDeposit).filter(FixedDeposit.id == fd_id, FixedDeposit.user_id == current_user.id).first()
    if not db_fd:
        raise HTTPException(status_code=404, detail="Fixed Deposit not found")
    
    for key, value in item.dict().items():
        setattr(db_fd, key, value)
    
    db.commit()
    db.refresh(db_fd)
    return db_fd
