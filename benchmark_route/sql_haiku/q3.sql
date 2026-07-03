SELECT oi.product, SUM(oi.qty) AS total_qty
FROM order_items oi
JOIN orders o ON oi.order_id = o.id
WHERE o.status = 'paid'
GROUP BY oi.product
ORDER BY total_qty DESC, product ASC;
