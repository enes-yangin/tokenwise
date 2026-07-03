SELECT oi.product AS product,
       SUM(oi.qty) AS total_qty
FROM order_items oi
JOIN orders o ON o.id = oi.order_id AND o.status = 'paid'
GROUP BY oi.product
ORDER BY total_qty DESC, product ASC;
