from typing import Any, Optional

from .base import AnalyticsService, BaseService


class PositionService(AnalyticsService):
    def _fetch(self, **filters: Any) -> list[dict]:
        with self._db.cursor() as cur:
            cur.execute("""SELECT p.*, c.symbol, c.unit FROM positions p
                           JOIN commodities c USING (commodity_id) ORDER BY c.symbol""")
            return cur.fetchall()

    def ladder(self, commodity_id: Optional[int] = None) -> list[dict]:
        with self._db.cursor() as cur:
            cur.execute("SELECT * FROM fn_position_ladder(%s)", (commodity_id,))
            return cur.fetchall()


class PnLService(AnalyticsService):
    def _fetch(self, **filters: Any) -> list[dict]:
        with self._db.cursor() as cur:
            cur.execute("SELECT * FROM fn_pnl_summary()")
            return cur.fetchall()

    def report(self, **filters: Any) -> dict:
        result = super().report(**filters)
        result["total_pnl"] = sum((r["total_pnl"] for r in result["rows"]), 0)
        return result


class ExposureService(AnalyticsService):
    def _fetch(self, **filters: Any) -> list[dict]:
        with self._db.cursor() as cur:
            cur.execute("SELECT * FROM fn_counterparty_exposure(%s)", (filters.get("counterparty_id"),))
            return cur.fetchall()


class AuditService(BaseService):
    def history(self, record_id: Optional[int] = None, limit: int = 100) -> list[dict]:
        sql, params = "SELECT * FROM audit_log", []
        if record_id is not None:
            sql += " WHERE table_name = 'trades' AND record_id = %s"
            params.append(record_id)
        sql += " ORDER BY audit_id DESC LIMIT %s"
        with self._db.cursor() as cur:
            cur.execute(sql, [*params, limit])
            return cur.fetchall()
