from typing import Optional

from fastapi import APIRouter, Depends, Query

from ..deps import get_user, trade_svc
from ..schemas import TradeCreate, TradeUpdate

router = APIRouter(prefix="/trades", tags=["trades"])


@router.post("", status_code=201)
def create_trade(body: TradeCreate, svc=Depends(trade_svc), user: str = Depends(get_user)):
    return svc.create(body.model_dump(), user)


@router.get("")
def list_trades(commodity_id: Optional[int] = None, counterparty_id: Optional[int] = None,
                status: Optional[str] = Query(default=None, pattern="^(ACTIVE|CANCELLED)$"),
                limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0),
                svc=Depends(trade_svc)):
    return svc.list(commodity_id, counterparty_id, status, limit, offset)


@router.get("/{trade_id}")
def get_trade(trade_id: int, svc=Depends(trade_svc)):
    return svc.get(trade_id)


@router.patch("/{trade_id}")
def amend_trade(trade_id: int, body: TradeUpdate, svc=Depends(trade_svc),
                user: str = Depends(get_user)):
    return svc.update(trade_id, body.model_dump(), user)


@router.post("/{trade_id}/cancel")
def cancel_trade(trade_id: int, svc=Depends(trade_svc), user: str = Depends(get_user)):
    return svc.cancel(trade_id, user)
