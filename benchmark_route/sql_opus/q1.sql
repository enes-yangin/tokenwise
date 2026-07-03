SELECT c.name AS name,
       SUM(oi.qty * oi.unit_price_cents) AS revenue_cents
FROM customers c
JOIN orders o ON o.customer_id = c.id AND o.status = 'paid'
JOIN order_items oi ON oi.order_id = o.id
GROUP BY c.id, c.name
ORDER BY revenue_cents DESC, name ASC;
