SELECT c.name, SUM(oi.qty * oi.unit_price_cents) AS revenue_cents
FROM customers c
JOIN orders o ON c.id = o.customer_id
JOIN order_items oi ON o.id = oi.order_id
WHERE o.status = 'paid'
GROUP BY c.id, c.name
ORDER BY revenue_cents DESC, name ASC;
