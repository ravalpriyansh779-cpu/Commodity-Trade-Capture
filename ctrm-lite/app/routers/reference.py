from fastapi import APIRouter, Depends

from ..deps import commodity_svc, counterparty_svc, price_svc
from ..schemas import CommodityIn, CounterpartyIn, MarketPriceIn

router = APIRouter()


@router.get("/commodities", tags=["reference"])
def list_commodities(svc=Depends(commodity_svc)):
    return svc.list_all()


@router.post("/commodities", status_code=201, tags=["reference"])
def create_commodity(body: CommodityIn, svc=Depends(commodity_svc)):
    return svc.create(body.model_dump())


@router.get("/commodities/{item_id}", tags=["reference"])
def get_commodity(item_id: int, svc=Depends(commodity_svc)):
    return svc.get(item_id)


@router.get("/counterparties", tags=["reference"])
def list_counterparties(svc=Depends(counterparty_svc)):
    return svc.list_all()


@router.post("/counterparties", status_code=201, tags=["reference"])
def create_counterparty(body: CounterpartyIn, svc=Depends(counterparty_svc)):
    return svc.create(body.model_dump())


@router.get("/counterparties/{item_id}", tags=["reference"])
def get_counterparty(item_id: int, svc=Depends(counterparty_svc)):
    return svc.get(item_id)


@router.put("/market-prices", tags=["reference"])
def upsert_price(body: MarketPriceIn, svc=Depends(price_svc)):
    return svc.upsert(body.model_dump())


@router.get("/market-prices/latest", tags=["reference"])
def latest_prices(svc=Depends(price_svc)):
    return svc.latest()
