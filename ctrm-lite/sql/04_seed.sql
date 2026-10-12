INSERT INTO commodities (symbol, name, unit, category) VALUES
 ('BRENT','Brent Crude Oil','BBL','ENERGY'),
 ('NG','Natural Gas','MMBTU','ENERGY'),
 ('CU','Copper','MT','METALS'),
 ('WHEAT','Wheat','BU','AGRICULTURE');

INSERT INTO counterparties (name, country, credit_limit) VALUES
 ('Vitol Trading','CH',50000000),
 ('Reliance Industries','IN',30000000),
 ('Glencore Intl','CH',40000000),
 ('Cargill Inc','US',20000000);

INSERT INTO market_prices (commodity_id, price_date, price)
SELECT c.commodity_id, CURRENT_DATE - d.ago, b.base + d.delta
FROM (VALUES ('BRENT',82.0),('NG',3.1),('CU',8800.0),('WHEAT',6.2)) AS b(sym, base)
JOIN commodities c ON c.symbol = b.sym
CROSS JOIN (VALUES (2, -0.05), (1, 0.02), (0, 0.10)) AS d(ago, delta);

SELECT set_config('app.current_user', 'seed', false);

INSERT INTO trades (commodity_id, counterparty_id, side, quantity, price, trade_date, delivery_start, delivery_end)
SELECT c.commodity_id, cp.counterparty_id, v.side, v.qty, v.px, CURRENT_DATE - v.ago,
       CURRENT_DATE + 30, CURRENT_DATE + 60
FROM (VALUES
  ('BRENT','Vitol Trading','BUY', 10000, 80.50, 5),
  ('BRENT','Glencore Intl','SELL', 4000, 83.00, 3),
  ('BRENT','Reliance Industries','BUY', 2000, 81.75, 1),
  ('NG','Cargill Inc','SELL', 50000, 3.30, 4),
  ('NG','Vitol Trading','BUY', 20000, 3.05, 2),
  ('CU','Glencore Intl','BUY', 500, 8700.00, 6),
  ('WHEAT','Cargill Inc','BUY', 100000, 6.00, 3)
) AS v(sym, cpty, side, qty, px, ago)
JOIN commodities c ON c.symbol = v.sym
JOIN counterparties cp ON cp.name = v.cpty;

SELECT set_config('app.current_user', '', false);
CALL sp_refresh_positions();
