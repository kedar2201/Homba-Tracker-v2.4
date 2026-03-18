from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models.other_asset import OtherAsset
from ..schemas.other_asset import OtherAssetSchema
from ..auth.auth import get_current_user
from ..models.user import User

router = APIRouter(tags=["Other Assets"])

@router.get("/", response_model=List[OtherAssetSchema])
def get_other_assets(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(OtherAsset).filter(OtherAsset.user_id == current_user.id).all()

from ..schemas.other_asset import OtherAssetCreate

@router.post("/", response_model=OtherAssetSchema)
def create_other_asset(
    asset: OtherAssetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_asset = OtherAsset(**asset.dict(), user_id=current_user.id)
    db.add(db_asset)
    db.commit()
    db.refresh(db_asset)
    return db_asset

@router.get("/summary")
def get_other_assets_summary(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    assets = db.query(OtherAsset).filter(OtherAsset.user_id == current_user.id).all()
    summary = {}
    for a in assets:
        cat = a.category.value
        summary[cat] = round(summary.get(cat, 0) + a.valuation, 2)
    return summary

from ..schemas.other_asset import OtherAssetUpdate

@router.put("/{asset_id}", response_model=OtherAssetSchema)
def update_other_asset(
    asset_id: int, 
    asset_update: OtherAssetUpdate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    asset = db.query(OtherAsset).filter(OtherAsset.id == asset_id, OtherAsset.user_id == current_user.id).first()
    if not asset:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Asset not found")
        
    for key, value in asset_update.dict(exclude_unset=True).items():
        setattr(asset, key, value)
        
    db.commit()
    db.refresh(asset)
    return asset
