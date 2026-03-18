from pydantic import BaseModel
from typing import Optional
from enum import Enum

class AssetCategory(str, Enum):
    INSURANCE = "INSURANCE"
    RETIREMENT = "RETIREMENT"
    REAL_ESTATE = "REAL_ESTATE"
    GOLD = "GOLD"
    BOND = "BOND"
    SAVINGS = "SAVINGS"
    MISC = "MISC"

class OtherAssetBase(BaseModel):
    category: AssetCategory
    name: str
    institution: Optional[str] = None
    valuation: float
    description: Optional[str] = None

class OtherAssetCreate(OtherAssetBase):
    pass

class OtherAssetUpdate(BaseModel):
    category: Optional[AssetCategory] = None
    name: Optional[str] = None
    institution: Optional[str] = None
    valuation: Optional[float] = None
    description: Optional[str] = None

class OtherAssetSchema(OtherAssetBase):
    id: int
    user_id: int

    class Config:
        from_attributes = True
