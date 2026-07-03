SELECT c.country AS country,
       COUNT(*) AS order_count
FROM customers c
JOIN orders o ON o.customer_id = c.id AND o.status = 'paid'
GROUP BY c.country
ORDER BY order_count DESC, country ASC;
