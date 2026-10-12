from typing import Optional

from fastapi import APIRouter, Depends

from ..deps import audit_svc, exposure_svc, pnl_svc, position_svc

router = APIRouter(tags=["analytics"])


@router.get("/positions")
def positions(svc=Depends(position_svc)):
    return svc.report()


@router.get("/positions/ladder")
def ladder(commodity_id: Optional[int] = None, svc=Depends(position_svc)):
    return svc.ladder(commodity_id)


@router.get("/pnl")
def pnl(svc=Depends(pnl_svc)):
    return svc.report()


@router.get("/exposure")
def exposure(counterparty_id: Optional[int] = None, svc=Depends(exposure_svc)):
    return svc.report(counterparty_id=counterparty_id)


@router.get("/audit")
def audit(trade_id: Optional[int] = None, limit: int = 100, svc=Depends(audit_svc)):
    return svc.history(trade_id, limit)
