from .base import ReferenceDataService, BaseService


class CommodityService(ReferenceDataService):
    _table = "commodities"
    _pk = "commodity_id"
    _columns = ("symbol", "name", "unit", "category")


class CounterpartyService(ReferenceDataService):
    _table = "counterparties"
    _pk = "counterparty_id"
    _columns = ("name", "country", "credit_limit")


class MarketPriceService(BaseService):
    def upsert(self, data: dict) -> dict:
        with self._translate_db_errors(), self._db.cursor() as cur:
            cur.execute(
                """INSERT INTO market_prices (commodity_id, price_date, price)
                   VALUES (%(commodity_id)s, %(price_date)s, %(price)s)
                   ON CONFLICT (commodity_id, price_date) DO UPDATE SET price = EXCLUDED.price
                   RETURNING *""", data)
            return cur.fetchone()

    def latest(self) -> list[dict]:
        with self._db.cursor() as cur:
            cur.execute(
                """SELECT DISTINCT ON (m.commodity_id) m.commodity_id, c.symbol, m.price_date, m.price
                   FROM market_prices m JOIN commodities c USING (commodity_id)
                   ORDER BY m.commodity_id, m.price_date DESC""")
            return cur.fetchall()
