from contextlib import contextmanager
from typing import Iterator

from psycopg import Cursor
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool


class Database:
    """Owns the connection pool. One transaction per `cursor()` block;
    the acting user is stamped on the transaction so DB audit triggers can read it."""

    def __init__(self, dsn: str) -> None:
        self._pool = ConnectionPool(
            dsn, min_size=1, max_size=10, open=False, kwargs={"row_factory": dict_row}
        )

    def open(self) -> None:
        self._pool.open()

    def close(self) -> None:
        self._pool.close()

    @contextmanager
    def cursor(self, user: str = "api") -> Iterator[Cursor]:
        with self._pool.connection() as conn:  # commits on success, rolls back on error
            with conn.cursor() as cur:
                cur.execute("SELECT set_config('app.current_user', %s, true)", (user,))
                yield cur
