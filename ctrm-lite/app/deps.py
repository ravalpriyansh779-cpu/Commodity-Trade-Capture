from fastapi import Header, Request

from .services.analytics import AuditService, ExposureService, PnLService, PositionService
from .services.reference import CommodityService, CounterpartyService, MarketPriceService
from .services.trade_service import TradeService


def get_user(x_user: str = Header(default="api")) -> str:
    return x_user


def _db(request: Request):
    return request.app.state.db


def commodity_svc(request: Request): return CommodityService(_db(request))
def counterparty_svc(request: Request): return CounterpartyService(_db(request))
def price_svc(request: Request): return MarketPriceService(_db(request))
def trade_svc(request: Request): return TradeService(_db(request))
def position_svc(request: Request): return PositionService(_db(request))
def pnl_svc(request: Request): return PnLService(_db(request))
def exposure_svc(request: Request): return ExposureService(_db(request))
def audit_svc(request: Request): return AuditService(_db(request))
