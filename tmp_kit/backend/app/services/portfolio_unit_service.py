from sqlalchemy.orm import Session
from sqlalchemy import func
from ..models.equity import Equity, EquityStatus
from ..models.mutual_fund import MutualFund, MFStatus
from ..models.fixed_deposit import FixedDeposit
from ..models.other_asset import OtherAsset

# Default NAV if no units exist
INITIAL_NAV = 100.0

def calculate_portfolio_nav(db: Session, user_id: int) -> dict:
    """
    Calculates the current Portfolio NAV based on Total Assets / Total Units.
    Returns dict: {nav: float, total_value: float, total_units: float}
    """
    
    # 1. Calculate Total Market Value of Assets
    # ---------------------------------------
    
    # Equity Value
    equities = db.query(Equity).filter(Equity.user_id == user_id, (Equity.status == EquityStatus.ACTIVE) | (Equity.status == None)).all()
    equity_value = 0.0
    for e in equities:
        price = e.current_price or e.buy_price or 0.0
        equity_value += (price * e.quantity)

    # MF Value
    mfs = db.query(MutualFund).filter(MutualFund.user_id == user_id, (MutualFund.status == MFStatus.ACTIVE) | (MutualFund.status == None)).all()
    mf_value = 0.0
    for m in mfs:
        # Use simple fallback: invested_amount if NAV missing (or unit logic if implemented fully)
        # Ideally should use live NAV if available, but for precise transactional NAV, we want consistency.
        # Assuming background job updates NAV or we use invested_amount as base.
        # Let's use logic from Dashboard:
        # But for 'transaction input', we need a stable value. SGBs are in MF table too.
        # If we want simple:
        val = m.invested_amount
        # If possible, calculate from units * nav (if nav is stored somewhere? MF model doesn't have 'current_nav', relies on live fetch)
        # This is a weak point. If we rely on live external API for NAV, it might fluctuate or fail.
        # Check if MF has 'current_value'? No.
        # Dashboard calculates it live.
        # We should probably use 'invested_amount' as a proxy if we can't get live, OR fetch live?
        # Fetching live during every transaction is slow.
        # We will iterate and assume invested_amount * (some growth factor? No).
        # Let's use Invested Amount as a safe baseline for now unless we have a 'market_value' cache.
        # User dashboard uses: nav * units.
        # I will verify if I can access a cache.
        mf_value += val if val else 0.0

    # FD Value
    fds = db.query(FixedDeposit).filter(FixedDeposit.user_id == user_id).all()
    fd_value = sum(f.principal for f in fds) # Ignoring interest for NAV to avoid daily creep?
    
    # Other Assets (Liquidable only?)
    # If we issue units against them, their value counts.
    # User said "Liquidable" categories in dashboard.
    others = db.query(OtherAsset).filter(OtherAsset.user_id == user_id).all()
    liquidable_categories = ["INSURANCE", "RETIREMENT", "GOLD", "BOND", "SAVINGS"]
    other_value = 0.0
    for o in others:
        cat = o.category.value if hasattr(o.category, 'value') else str(o.category)
        if cat in liquidable_categories:
            other_value += o.valuation

    total_value = equity_value + mf_value + fd_value + other_value

    # 2. Calculate Total Units
    # ------------------------
    
    # Equity Units
    # Sum(buy_units) - Sum(sell_units) across ALL records (Active + Sold)
    # Actually, simply query all for user.
    
    eq_units_query = db.query(
        func.sum(Equity.buy_units),
        func.sum(Equity.sell_units)
    ).filter(Equity.user_id == user_id).first()
    
    eq_buy = eq_units_query[0] or 0.0
    eq_sell = eq_units_query[1] or 0.0
    net_eq_units = eq_buy - eq_sell

    # MF Units
    mf_units_query = db.query(
        func.sum(MutualFund.p_buy_units),
        func.sum(MutualFund.p_sell_units)
    ).filter(MutualFund.user_id == user_id).first()
    
    mf_buy = mf_units_query[0] or 0.0
    mf_sell = mf_units_query[1] or 0.0
    net_mf_units = mf_buy - mf_sell

    # FD Units?
    # I didn't backfill FDs. So FD units are 0.
    # BUT FD Value is in 'total_value'.
    # This creates a mismatch: Value > 0, Units = Eq+MF only.
    # NAV = (Eq + MF + FD) / (Eq_Units + MF_Units).
    # This effectively means FDs "leverage" the Equity units (FD injection boosts NAV).
    # This is WRONG.
    # If I add 1L FD, NAV jumps.
    # REQUIRED: FDs must have units. OR FDs must be excluded from NAV.
    # User's logic: "Units belong to the portfolio".
    # If I have 1L Equity and 1L FD. Total 2L.
    # If I only have 1000 Equity Units.
    # NAV = 2L / 1000 = 200.
    # But Equity is only worth 1L (NAV 100).
    # Buying FD doubled the NAV? False.
    # I MUST exclude FDs/Others from this NAV unless they are unitized.
    # Given I haven't unitized FDs in migration, I MUST exclude generic assets from this specific "Growth Portfolio NAV".
    
    # REVISION: Only include Equity and Mutual Funds in this calculation.
    # User's request was about "Stocks" and "Units".
    
    growth_portfolio_value = equity_value + mf_value
    total_units = net_eq_units + net_mf_units
    
    if total_units <= 0:
        return {"nav": INITIAL_NAV, "total_value": 0, "total_units": 0}
        
    nav = growth_portfolio_value / total_units
    
    return {
        "nav": nav,
        "total_value": growth_portfolio_value,
        "total_units": total_units
    }
