SELECT c.country, COUNT(*) AS order_count
FROM customers c
JOIN orders o ON c.id = o.customer_id
WHERE o.status = 'paid'
GROUP BY c.country
ORDER BY order_count DESC, country ASC;
