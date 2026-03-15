from sqlalchemy import Column, Integer, String, Float, ForeignKey, Enum
from sqlalchemy.orm import relationship
from ..database import Base
import enum

class AssetCategory(str, enum.Enum):
    INSURANCE = "INSURANCE"
    RETIREMENT = "RETIREMENT" # PPF, EPF
    REAL_ESTATE = "REAL_ESTATE" # Plots, Flats, Land
    GOLD = "GOLD"
    BOND = "BOND"
    SAVINGS = "SAVINGS"
    MISC = "MISC"

class OtherAsset(Base):
    __tablename__ = "other_assets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    category = Column(Enum(AssetCategory))
    name = Column(String) # e.g. "PPF Kedar"
    institution = Column(String, nullable=True) # e.g. "SBI", "LIC"
    valuation = Column(Float) # Principal or Current Value
    description = Column(String, nullable=True)

    user = relationship("User")
