# CTRM-lite — Commodity Trade Capture & P&L System

PostgreSQL + FastAPI. Trade capture, positions, P&L, counterparty exposure, audit trail.

## Run
```bash
docker compose up -d                 # Postgres; loads sql/01..04 automatically
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload        # docs: http://localhost:8000/docs
pytest -q tests                      # integration tests (need the DB above)
```
Without Docker: run `sql/01..04_*.sql` in order against any Postgres 14+ database.

## Database (`sql/`)
| File | Contents |
|---|---|
| 01_schema.sql | commodities, counterparties, trades, market_prices, positions, audit_log + constraints/indexes |
| 02_functions.sql | `fn_latest_price`, `sp_refresh_positions`, `sp_cancel_trade`, `fn_pnl_summary` (CTEs, FILTER aggregates), `fn_position_ladder` (window functions), `fn_counterparty_exposure` (LATERAL join, RANK) |
| 03_triggers.sql | `trg_trades_audit` (INSERT/UPDATE/DELETE → audit_log with field-level diffs), `updated_at` touch, append-only audit_log guard |
| 04_seed.sql | sample commodities, counterparties, prices, trades |

P&L: average-cost method. Realized = matched qty × (avg sell − avg buy); unrealized = open qty marked to latest market price.
Audit actor: the API sets `app.current_user` per transaction from the `X-User` header.

## API (`app/`)
- `POST/GET /trades`, `GET/PATCH /trades/{id}`, `POST /trades/{id}/cancel`
- `GET /positions`, `/positions/ladder`, `/pnl`, `/exposure`, `/audit?trade_id=`
- `POST/GET /commodities`, `/counterparties`; `PUT /market-prices`, `GET /market-prices/latest`

## OOP design (`app/services/`)
- **Abstraction**: `BaseService`, `ReferenceDataService`, `AnalyticsService`, `TradeValidator` are ABCs.
- **Inheritance**: `CommodityService`/`CounterpartyService` ← `ReferenceDataService`; `PositionService`/`PnLService`/`ExposureService` ← `AnalyticsService`.
- **Polymorphism**: `AnalyticsService.report()` calls subclass `_fetch()`; `TradeService` runs a list of `TradeValidator` strategies (active counterparty, price tolerance, credit limit).
- **Encapsulation**: DB handle, validators and SQL are private (`_db`, `_validators`); routers only see service methods.
