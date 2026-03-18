from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.user import User
from ..auth.auth import get_current_user
import io
import pandas as pd
import logging

router = APIRouter(prefix="/nav-upload", tags=["NAV Upload"])
logger = logging.getLogger(__name__)

# In-memory NAV cache from uploaded file
NAV_CACHE = {}

@router.post("/upload")
async def upload_nav_file(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    """
    Upload NAVOpen.txt file to update NAV values for mutual funds.
    Expected format: Scheme Code;ISIN;ISIN2;Scheme Name;NAV;Date
    """
    try:
        contents = await file.read()
        
        # Try to read as semicolon-separated
        try:
            df = pd.read_csv(io.BytesIO(contents), sep=';', encoding='utf-8')
        except:
            try:
                df = pd.read_csv(io.BytesIO(contents), sep=';', encoding='cp1252')
            except:
                raise HTTPException(status_code=400, detail="Could not parse NAV file. Expected semicolon-separated format.")
        
        # Clear existing cache
        NAV_CACHE.clear()
        
        processed = 0
        for _, row in df.iterrows():
            try:
                # Expected columns: Scheme Code, ISIN, ISIN2, Scheme Name, NAV, Date
                if len(row) < 5:
                    continue
                    
                scheme_code = str(row.iloc[0]).strip()
                isin1 = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else None
                isin2 = str(row.iloc[2]).strip() if pd.notna(row.iloc[2]) else None
                scheme_name = str(row.iloc[3]).strip().upper()
                nav_value = str(row.iloc[4]).strip()
                
                if nav_value.lower() == 'n.a.' or not nav_value:
                    continue
                    
                nav = float(nav_value)
                
                # Store by scheme code
                if scheme_code and scheme_code != '-':
                    NAV_CACHE[f"CODE:{scheme_code}"] = nav
                    
                # Store by ISIN
                if isin1 and isin1 != '-':
                    NAV_CACHE[f"ISIN:{isin1}"] = nav
                if isin2 and isin2 != '-':
                    NAV_CACHE[f"ISIN:{isin2}"] = nav
                    
                # Store by scheme name
                NAV_CACHE[f"NAME:{scheme_name}"] = nav
                
                processed += 1
                
            except Exception as e:
                logger.warning(f"Error processing row: {e}")
                continue
        
        return {
            "status": "success",
            "message": f"Processed {processed} NAV entries",
            "total_cached": len(NAV_CACHE)
        }
        
    except Exception as e:
        logger.error(f"Error uploading NAV file: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to process NAV file: {str(e)}")

@router.get("/status")
def get_nav_cache_status(current_user: User = Depends(get_current_user)):
    """Get current NAV cache status"""
    return {
        "cached_entries": len(NAV_CACHE),
        "has_data": len(NAV_CACHE) > 0
    }

def get_nav_from_cache(amfi_code=None, isin=None, scheme_name=None):
    """
    Retrieve NAV from uploaded cache.
    Returns None if not found.
    """
    if not NAV_CACHE:
        return None
        
    # Try AMFI code first
    if amfi_code:
        nav = NAV_CACHE.get(f"CODE:{amfi_code}")
        if nav:
            return nav
            
    # Try ISIN
    if isin:
        nav = NAV_CACHE.get(f"ISIN:{isin}")
        if nav:
            return nav
            
    # Try scheme name
    if scheme_name:
        clean_name = scheme_name.upper().strip()
        nav = NAV_CACHE.get(f"NAME:{clean_name}")
        if nav:
            return nav
            
    return None
