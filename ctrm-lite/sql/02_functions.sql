-- Latest market price for a commodity
CREATE OR REPLACE FUNCTION fn_latest_price(p_commodity_id INT)
RETURNS NUMERIC LANGUAGE sql STABLE AS $$
    SELECT price FROM market_prices
    WHERE commodity_id = p_commodity_id
    ORDER BY price_date DESC LIMIT 1;
$$;

-- Rebuild positions table from ACTIVE trades
CREATE OR REPLACE PROCEDURE sp_refresh_positions()
LANGUAGE plpgsql AS $$
BEGIN
    DELETE FROM positions;
    INSERT INTO positions (commodity_id, buy_quantity, sell_quantity, net_quantity, avg_buy_price, avg_sell_price)
    SELECT t.commodity_id,
           COALESCE(SUM(t.quantity) FILTER (WHERE t.side = 'BUY'), 0),
           COALESCE(SUM(t.quantity) FILTER (WHERE t.side = 'SELL'), 0),
           COALESCE(SUM(t.quantity) FILTER (WHERE t.side = 'BUY'), 0)
         - COALESCE(SUM(t.quantity) FILTER (WHERE t.side = 'SELL'), 0),
           ROUND(SUM(t.quantity * t.price) FILTER (WHERE t.side = 'BUY')
                 / NULLIF(SUM(t.quantity) FILTER (WHERE t.side = 'BUY'), 0), 4),
           ROUND(SUM(t.quantity * t.price) FILTER (WHERE t.side = 'SELL')
                 / NULLIF(SUM(t.quantity) FILTER (WHERE t.side = 'SELL'), 0), 4)
    FROM trades t
    WHERE t.status = 'ACTIVE'
    GROUP BY t.commodity_id;
END;
$$;

-- Cancel a trade, then refresh positions
CREATE OR REPLACE PROCEDURE sp_cancel_trade(p_trade_id BIGINT)
LANGUAGE plpgsql AS $$
BEGIN
    UPDATE trades SET status = 'CANCELLED'
    WHERE trade_id = p_trade_id AND status = 'ACTIVE';
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Trade % not found or not active', p_trade_id;
    END IF;
    CALL sp_refresh_positions();
END;
$$;

-- Real-time P&L per commodity (average-cost method).
-- realized   = matched qty * (avg sell - avg buy)
-- unrealized = open qty marked to latest market price
CREATE OR REPLACE FUNCTION fn_pnl_summary()
RETURNS TABLE (
    commodity_id INT, symbol VARCHAR, net_quantity NUMERIC,
    avg_buy_price NUMERIC, avg_sell_price NUMERIC, market_price NUMERIC,
    realized_pnl NUMERIC, unrealized_pnl NUMERIC, total_pnl NUMERIC
) LANGUAGE sql STABLE AS $$
    WITH agg AS (
        SELECT t.commodity_id AS cid,
               COALESCE(SUM(t.quantity) FILTER (WHERE t.side = 'BUY'), 0)  AS buy_qty,
               COALESCE(SUM(t.quantity) FILTER (WHERE t.side = 'SELL'), 0) AS sell_qty,
               SUM(t.quantity * t.price) FILTER (WHERE t.side = 'BUY')  AS buy_val,
               SUM(t.quantity * t.price) FILTER (WHERE t.side = 'SELL') AS sell_val
        FROM trades t WHERE t.status = 'ACTIVE'
        GROUP BY t.commodity_id
    ), calc AS (
        SELECT cid, buy_qty - sell_qty AS net_qty, LEAST(buy_qty, sell_qty) AS matched_qty,
               buy_val  / NULLIF(buy_qty, 0)  AS avg_buy,
               sell_val / NULLIF(sell_qty, 0) AS avg_sell,
               fn_latest_price(cid) AS mkt
        FROM agg
    ), pnl AS (
        SELECT cid, net_qty, avg_buy, avg_sell, mkt,
               COALESCE(matched_qty * (avg_sell - avg_buy), 0) AS realized,
               COALESCE(CASE WHEN net_qty > 0 THEN  net_qty * (mkt - avg_buy)
                             WHEN net_qty < 0 THEN -net_qty * (avg_sell - mkt)
                             ELSE 0 END, 0) AS unrealized
        FROM calc
    )
    SELECT p.cid, cm.symbol, p.net_qty,
           ROUND(p.avg_buy, 4), ROUND(p.avg_sell, 4), p.mkt,
           ROUND(p.realized, 2), ROUND(p.unrealized, 2),
           ROUND(p.realized + p.unrealized, 2)
    FROM pnl p
    JOIN commodities cm ON cm.commodity_id = p.cid
    ORDER BY cm.symbol;
$$;

-- Trade-by-trade position ladder using window functions
CREATE OR REPLACE FUNCTION fn_position_ladder(p_commodity_id INT DEFAULT NULL)
RETURNS TABLE (
    trade_id BIGINT, trade_ref VARCHAR, symbol VARCHAR, trade_date DATE,
    side VARCHAR, quantity NUMERIC, price NUMERIC,
    cumulative_position NUMERIC, cumulative_cash_flow NUMERIC, trade_seq BIGINT
) LANGUAGE sql STABLE AS $$
    SELECT t.trade_id, t.trade_ref, cm.symbol, t.trade_date, t.side, t.quantity, t.price,
           SUM(CASE WHEN t.side = 'BUY' THEN t.quantity ELSE -t.quantity END) OVER w,
           SUM(CASE WHEN t.side = 'BUY' THEN -t.quantity * t.price ELSE t.quantity * t.price END) OVER w,
           ROW_NUMBER() OVER w
    FROM trades t
    JOIN commodities cm ON cm.commodity_id = t.commodity_id
    WHERE t.status = 'ACTIVE'
      AND (p_commodity_id IS NULL OR t.commodity_id = p_commodity_id)
    WINDOW w AS (PARTITION BY t.commodity_id ORDER BY t.trade_date, t.trade_id)
    ORDER BY cm.symbol, t.trade_date, t.trade_id;
$$;

-- Counterparty exposure: gross notional, mark-to-market, credit utilisation
CREATE OR REPLACE FUNCTION fn_counterparty_exposure(p_counterparty_id INT DEFAULT NULL)
RETURNS TABLE (
    counterparty_id INT, name VARCHAR, credit_limit NUMERIC,
    gross_notional NUMERIC, mtm NUMERIC, utilization_pct NUMERIC, exposure_rank BIGINT
) LANGUAGE sql STABLE AS $$
    SELECT cp.counterparty_id, cp.name, cp.credit_limit,
           COALESCE(SUM(t.quantity * t.price), 0)::NUMERIC(18,2),
           COALESCE(SUM(CASE WHEN t.side = 'BUY' THEN t.quantity * (lp.price - t.price)
                             ELSE t.quantity * (t.price - lp.price) END), 0)::NUMERIC(18,2),
           ROUND(100 * COALESCE(SUM(t.quantity * t.price), 0) / NULLIF(cp.credit_limit, 0), 2),
           RANK() OVER (ORDER BY COALESCE(SUM(t.quantity * t.price), 0) DESC)
    FROM counterparties cp
    LEFT JOIN trades t ON t.counterparty_id = cp.counterparty_id AND t.status = 'ACTIVE'
    LEFT JOIN LATERAL (
        SELECT mp.price FROM market_prices mp
        WHERE mp.commodity_id = t.commodity_id
        ORDER BY mp.price_date DESC LIMIT 1
    ) lp ON TRUE
    WHERE (p_counterparty_id IS NULL OR cp.counterparty_id = p_counterparty_id)
    GROUP BY cp.counterparty_id, cp.name, cp.credit_limit
    ORDER BY 7, cp.name;
$$;
