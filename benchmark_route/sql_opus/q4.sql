SELECT c.name AS name
FROM customers c
WHERE NOT EXISTS (
    SELECT 1 FROM orders o
    WHERE o.customer_id = c.id AND o.status = 'paid'
)
ORDER BY name ASC;
