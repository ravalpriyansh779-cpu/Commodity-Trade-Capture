from typing import Optional, Sequence

from ..db import Database
from ..errors import ConflictError, NotFoundError
from .base import BaseService
from .validators import (ActiveCounterpartyValidator, CreditLimitValidator,
                         PriceToleranceValidator, TradeValidator)


class TradeService(BaseService):
    def __init__(self, db: Database, validators: Optional[Sequence[TradeValidator]] = None) -> None:
        super().__init__(db)
        self._validators = list(validators) if validators is not None else [
            ActiveCounterpartyValidator(), PriceToleranceValidator(), CreditLimitValidator()]

    def _run_validators(self, cur, trade: dict, existing: Optional[dict] = None) -> None:
        for v in self._validators:  # polymorphic dispatch
            v.validate(cur, trade, existing)

    @staticmethod
    def _fetch(cur, trade_id: int) -> Optional[dict]:
        cur.execute("SELECT * FROM trades WHERE trade_id = %s", (trade_id,))
        return cur.fetchone()

    def create(self, data: dict, user: str) -> dict:
        with self._translate_db_errors(), self._db.cursor(user) as cur:
            self._run_validators(cur, data)
            cur.execute(
                """INSERT INTO trades (commodity_id, counterparty_id, side, quantity, price, currency,
                                       trade_date, delivery_start, delivery_end)
                   VALUES (%(commodity_id)s, %(counterparty_id)s, %(side)s, %(quantity)s, %(price)s,
                           %(currency)s, COALESCE(%(trade_date)s, CURRENT_DATE),
                           %(delivery_start)s, %(delivery_end)s)
                   RETURNING *""", data)
            trade = cur.fetchone()
            cur.execute("CALL sp_refresh_positions()")
            return trade

    def get(self, trade_id: int) -> dict:
        with self._db.cursor() as cur:
            trade = self._fetch(cur, trade_id)
        if not trade:
            raise NotFoundError(f"Trade {trade_id} not found")
        return trade

    def list(self, commodity_id: Optional[int] = None, counterparty_id: Optional[int] = None,
             status: Optional[str] = None, limit: int = 100, offset: int = 0) -> list[dict]:
        where, params = [], []
        for col, val in (("commodity_id", commodity_id), ("counterparty_id", counterparty_id),
                         ("status", status)):
            if val is not None:
                where.append(f"{col} = %s")
                params.append(val)
        sql = "SELECT * FROM trades"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY trade_id DESC LIMIT %s OFFSET %s"
        with self._db.cursor() as cur:
            cur.execute(sql, [*params, limit, offset])
            return cur.fetchall()

    def update(self, trade_id: int, changes: dict, user: str) -> dict:
        changes = {k: v for k, v in changes.items() if v is not None}
        with self._translate_db_errors(), self._db.cursor(user) as cur:
            existing = self._fetch(cur, trade_id)
            if not existing:
                raise NotFoundError(f"Trade {trade_id} not found")
            if existing["status"] != "ACTIVE":
                raise ConflictError("Cancelled trades cannot be modified")
            if not changes:
                return existing
            merged = {**existing, **changes}
            self._run_validators(cur, merged, existing)
            sets = ", ".join(f"{k} = %({k})s" for k in changes)  # keys limited by TradeUpdate schema
            cur.execute(f"UPDATE trades SET {sets} WHERE trade_id = %(trade_id)s RETURNING *",
                        {**changes, "trade_id": trade_id})
            trade = cur.fetchone()
            cur.execute("CALL sp_refresh_positions()")
            return trade

    def cancel(self, trade_id: int, user: str) -> dict:
        with self._db.cursor(user) as cur:
            existing = self._fetch(cur, trade_id)
            if not existing:
                raise NotFoundError(f"Trade {trade_id} not found")
            if existing["status"] != "ACTIVE":
                raise ConflictError("Trade already cancelled")
            cur.execute("CALL sp_cancel_trade(%s)", (trade_id,))
            return self._fetch(cur, trade_id)
