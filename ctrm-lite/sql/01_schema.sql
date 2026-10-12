-- CTRM-lite: normalized schema
CREATE SEQUENCE trade_ref_seq START 1;

CREATE TABLE commodities (
    commodity_id SERIAL PRIMARY KEY,
    symbol       VARCHAR(16)  NOT NULL UNIQUE,
    name         VARCHAR(100) NOT NULL,
    unit         VARCHAR(16)  NOT NULL,
    category     VARCHAR(32)  NOT NULL CHECK (category IN ('ENERGY','METALS','AGRICULTURE'))
);

CREATE TABLE counterparties (
    counterparty_id SERIAL PRIMARY KEY,
    name            VARCHAR(150) NOT NULL UNIQUE,
    country         CHAR(2)      NOT NULL,
    credit_limit    NUMERIC(18,2) NOT NULL CHECK (credit_limit >= 0),
    is_active       BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE market_prices (
    commodity_id INT  NOT NULL REFERENCES commodities(commodity_id),
    price_date   DATE NOT NULL,
    price        NUMERIC(18,4) NOT NULL CHECK (price > 0),
    PRIMARY KEY (commodity_id, price_date)
);

CREATE TABLE trades (
    trade_id        BIGSERIAL PRIMARY KEY,
    trade_ref       VARCHAR(32) NOT NULL UNIQUE
                    DEFAULT ('TRD-' || lpad(nextval('trade_ref_seq')::text, 8, '0')),
    commodity_id    INT NOT NULL REFERENCES commodities(commodity_id),
    counterparty_id INT NOT NULL REFERENCES counterparties(counterparty_id),
    side            VARCHAR(4)  NOT NULL CHECK (side IN ('BUY','SELL')),
    quantity        NUMERIC(18,4) NOT NULL CHECK (quantity > 0),
    price           NUMERIC(18,4) NOT NULL CHECK (price > 0),
    currency        CHAR(3) NOT NULL DEFAULT 'USD',
    trade_date      DATE NOT NULL DEFAULT CURRENT_DATE,
    delivery_start  DATE NOT NULL,
    delivery_end    DATE NOT NULL,
    status          VARCHAR(10) NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE','CANCELLED')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (delivery_end >= delivery_start)
);
CREATE INDEX idx_trades_commodity    ON trades(commodity_id) WHERE status = 'ACTIVE';
CREATE INDEX idx_trades_counterparty ON trades(counterparty_id) WHERE status = 'ACTIVE';
CREATE INDEX idx_trades_date         ON trades(trade_date);

-- Net position per commodity (refreshed by sp_refresh_positions)
CREATE TABLE positions (
    commodity_id   INT PRIMARY KEY REFERENCES commodities(commodity_id),
    buy_quantity   NUMERIC(18,4) NOT NULL,
    sell_quantity  NUMERIC(18,4) NOT NULL,
    net_quantity   NUMERIC(18,4) NOT NULL,
    avg_buy_price  NUMERIC(18,4),
    avg_sell_price NUMERIC(18,4),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE audit_log (
    audit_id       BIGSERIAL PRIMARY KEY,
    table_name     TEXT NOT NULL,
    record_id      BIGINT NOT NULL,
    action         VARCHAR(6) NOT NULL CHECK (action IN ('INSERT','UPDATE','DELETE')),
    old_data       JSONB,
    new_data       JSONB,
    changed_fields JSONB,
    changed_by     TEXT NOT NULL,
    changed_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_audit_record ON audit_log(table_name, record_id, changed_at);
