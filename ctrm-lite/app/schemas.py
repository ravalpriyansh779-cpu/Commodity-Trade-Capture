from datetime import date
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator


class CommodityIn(BaseModel):
    symbol: str = Field(min_length=1, max_length=16)
    name: str
    unit: str
    category: Literal["ENERGY", "METALS", "AGRICULTURE"]


class CounterpartyIn(BaseModel):
    name: str
    country: str = Field(min_length=2, max_length=2)
    credit_limit: Decimal = Field(ge=0)


class MarketPriceIn(BaseModel):
    commodity_id: int
    price_date: date
    price: Decimal = Field(gt=0)


class TradeCreate(BaseModel):
    commodity_id: int
    counterparty_id: int
    side: Literal["BUY", "SELL"]
    quantity: Decimal = Field(gt=0)
    price: Decimal = Field(gt=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    trade_date: Optional[date] = None
    delivery_start: date
    delivery_end: date

    @model_validator(mode="after")
    def _dates(self):
        if self.delivery_end < self.delivery_start:
            raise ValueError("delivery_end must be on/after delivery_start")
        return self


class TradeUpdate(BaseModel):
    quantity: Optional[Decimal] = Field(default=None, gt=0)
    price: Optional[Decimal] = Field(default=None, gt=0)
    delivery_start: Optional[date] = None
    delivery_end: Optional[date] = None
