from abc import ABC, abstractmethod
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator

import psycopg.errors as pgerr

from ..db import Database
from ..errors import ConflictError, DomainError, ValidationFailed


class BaseService(ABC):
    """Abstract base: holds the (encapsulated) DB handle and maps DB errors to domain errors."""

    def __init__(self, db: Database) -> None:
        self._db = db

    @contextmanager
    def _translate_db_errors(self) -> Iterator[None]:
        try:
            yield
        except pgerr.UniqueViolation as e:
            raise ConflictError("Duplicate record") from e
        except pgerr.ForeignKeyViolation as e:
            raise ValidationFailed("Referenced record does not exist") from e
        except pgerr.CheckViolation as e:
            raise ValidationFailed("Value violates a database constraint") from e


class ReferenceDataService(BaseService):
    """Generic CRUD for simple reference tables. Subclasses declare table metadata."""

    @property
    @abstractmethod
    def _table(self) -> str: ...

    @property
    @abstractmethod
    def _pk(self) -> str: ...

    @property
    @abstractmethod
    def _columns(self) -> tuple[str, ...]: ...

    def list_all(self) -> list[dict]:
        with self._db.cursor() as cur:
            cur.execute(f"SELECT * FROM {self._table} ORDER BY {self._pk}")
            return cur.fetchall()

    def get(self, item_id: int) -> dict:
        with self._db.cursor() as cur:
            cur.execute(f"SELECT * FROM {self._table} WHERE {self._pk} = %s", (item_id,))
            row = cur.fetchone()
        if not row:
            from ..errors import NotFoundError
            raise NotFoundError(f"{self._table} id {item_id} not found")
        return row

    def create(self, data: dict[str, Any]) -> dict:
        cols = self._columns
        sql = (f"INSERT INTO {self._table} ({', '.join(cols)}) "
               f"VALUES ({', '.join(['%s'] * len(cols))}) RETURNING *")
        with self._translate_db_errors(), self._db.cursor() as cur:
            cur.execute(sql, [data[c] for c in cols])
            return cur.fetchone()


class AnalyticsService(BaseService):
    """Template method: subclasses implement `_fetch`; `report` wraps it uniformly (polymorphism)."""

    @abstractmethod
    def _fetch(self, **filters: Any) -> list[dict]: ...

    def report(self, **filters: Any) -> dict:
        rows = self._fetch(**filters)
        return {"as_of": datetime.now(timezone.utc).isoformat(), "count": len(rows), "rows": rows}


__all__ = ["BaseService", "ReferenceDataService", "AnalyticsService", "DomainError"]
