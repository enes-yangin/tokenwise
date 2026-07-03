INSERT INTO customers (id, name, country) VALUES
  (1, 'Alice', 'TR'),
  (2, 'Bob',   'TR'),
  (3, 'Carol', 'US'),
  (4, 'Dave',  'US');

INSERT INTO orders (id, customer_id, status) VALUES
  (1, 1, 'paid'),
  (2, 1, 'paid'),
  (3, 2, 'cancelled'),
  (4, 3, 'paid'),
  (5, 4, 'paid'),
  (6, 4, 'cancelled');

INSERT INTO order_items (id, order_id, product, qty, unit_price_cents) VALUES
  (1, 1, 'widget', 2, 100),
  (2, 1, 'gadget', 1, 300),
  (3, 2, 'widget', 1, 100),
  (4, 3, 'widget', 5, 100),
  (5, 4, 'gadget', 2, 300),
  (6, 5, 'widget', 3, 100),
  (7, 6, 'gadget', 10, 300);
