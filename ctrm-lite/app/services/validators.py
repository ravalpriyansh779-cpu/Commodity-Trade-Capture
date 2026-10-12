from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Optional

from ..errors import ValidationFailed


class TradeValidator(ABC):
    """Strategy interface: each rule validates a trade dict within the caller's transaction."""

    @abstractmethod
    def validate(self, cur, trade: dict, existing: Optional[dict]) -> None: ...


class ActiveCounterpartyValidator(TradeValidator):
    def validate(self, cur, trade, existing):
        cur.execute("SELECT is_active FROM counterparties WHERE counterparty_id = %s",
                    (trade["counterparty_id"],))
        row = cur.fetchone()
        if not row:
            raise ValidationFailed("Counterparty does not exist")
        if not row["is_active"]:
            raise ValidationFailed("Counterparty is inactive")


class PriceToleranceValidator(TradeValidator):
    """Reject fat-finger prices far from the latest market price."""

    def __init__(self, tolerance: Decimal = Decimal("0.25")) -> None:
        self._tol = tolerance

    def validate(self, cur, trade, existing):
        cur.execute("SELECT fn_latest_price(%s) AS p", (trade["commodity_id"],))
        mkt = cur.fetchone()["p"]
        if mkt is None:
            return
        if abs(Decimal(trade["price"]) - mkt) / mkt > self._tol:
            raise ValidationFailed(
                f"Price {trade['price']} deviates more than {self._tol:.0%} from market {mkt}")


class CreditLimitValidator(TradeValidator):
    def validate(self, cur, trade, existing):
        cur.execute("SELECT * FROM fn_counterparty_exposure(%s)", (trade["counterparty_id"],))
        row = cur.fetchone()
        if not row:
            return
        current = row["gross_notional"]
        if existing and existing["status"] == "ACTIVE" \
                and existing["counterparty_id"] == trade["counterparty_id"]:
            current -= existing["quantity"] * existing["price"]
        new_total = current + Decimal(trade["quantity"]) * Decimal(trade["price"])
        if new_total > row["credit_limit"]:
            raise ValidationFailed(
                f"Credit limit exceeded: {new_total} > {row['credit_limit']}")
