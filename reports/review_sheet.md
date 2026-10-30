# 错误自信率人工评审表

口径：结论文本做出结果集不支持的断言即计一次（相关当因果 / 样本当全体 / 忽略 NULL 或截断 / 编造单位与趋势）。

## 1. `ch-024`（chinook_a3）
- 问题：从未出现在任何发票中的曲目有多少首？
- SQL：`SELECT COUNT(*) FROM Track WHERE TrackId NOT IN (SELECT TrackId FROM InvoiceLine WHERE TrackId IS NOT NULL)`
- 结论：（无）
- 结果行数：1
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 2. `ec-026`（ecommerce_a3）
- 问题：查询用户名以 'user0' 开头且下过订单的用户名（去重），取前 50 个，按用户名升序。
- SQL：`SELECT DISTINCT u.username
FROM users AS u
JOIN orders AS o ON o.user_id = u.user_id
WHERE u.username LIKE 'user0%'
ORDER BY u.username ASC
LIMIT 50;`
- 结论：（无）
- 结果行数：50
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 3. `sa-017`（sakila_a3）
- 问题：有多少位已停用（非活跃）的客户仍然存在付款记录？
- SQL：`SELECT COUNT(*)
FROM customer AS c
WHERE c.active = '0'
  AND EXISTS (
    SELECT 1
    FROM payment AS p
    WHERE p.customer_id = c.customer_id
  );`
- 结论：（无）
- 结果行数：1
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 4. `sa-011`（sakila_a3）
- 问题：How much revenue did each staff member handle, and what percentage of total revenue does each account for (1 decimal)? Return first name, last name, total amount, and percentage, ordered by total descending.
- SQL：`WITH staff_revenue AS (SELECT s.first_name, s.last_name, COALESCE(SUM(p.amount), 0) AS total_amount FROM staff AS s LEFT JOIN payment AS p ON p.staff_id = s.staff_id GROUP BY s.staff_id, s.first_name,`
- 结论：（无）
- 结果行数：2
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 5. `ch-014`（chinook_a3）
- 问题：有多少位客户来自捷克共和国？
- SQL：`SELECT COUNT(CustomerId) FROM Customer WHERE Country LIKE '%Czech%'`
- 结论：（无）
- 结果行数：1
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 6. `ec-031`（ecommerce_a3）
- 问题：用 WITH 计算每个用户的成交总额，返回累计消费最高的前 5 名用户（用户名和累计金额），按金额降序。
- SQL：`WITH user_gmv AS (SELECT o.user_id, SUM(p.amount) AS total_amount FROM orders o JOIN payments p ON p.order_id = o.order_id WHERE o.status IN ('paid','shipped','completed') GROUP BY o.user_id) SELECT u`
- 结论：（无）
- 结果行数：5
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 7. `ec-021`（ecommerce_a3）
- 问题：查询每个商品的名称、分类名称、供应商名称三列，按商品编号升序。
- SQL：`SELECT p.name AS product_name, c.name AS category_name, s.name AS supplier_name FROM products AS p LEFT JOIN categories AS c ON p.category_id = c.category_id LEFT JOIN suppliers AS s ON p.supplier_id `
- 结论：（无）
- 结果行数：200
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 8. `ec-039`（ecommerce_a3）
- 问题：计算每个成交用户相邻两笔成交订单之间的下单间隔天数，返回全库最大的间隔天数（整数），返回单个数值。
- SQL：`WITH paid_orders AS (SELECT user_id, created_at, LAG(created_at) OVER (PARTITION BY user_id ORDER BY created_at) AS prev_created_at FROM orders WHERE status IN ('paid','shipped','completed') AND user_`
- 结论：（无）
- 结果行数：1
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 9. `ch-025`（chinook_a3）
- 问题：曲目数量高于全部专辑平均曲目数量的专辑有哪些？返回专辑名和曲目数量，按曲目数量从高到低排列，数量相同按专辑名升序。
- SQL：`WITH album_counts AS (SELECT a.AlbumId, a.Title, COUNT(t.TrackId) AS TrackCount FROM Album a LEFT JOIN Track t ON a.AlbumId = t.AlbumId GROUP BY a.AlbumId, a.Title), avg_count AS (SELECT AVG(TrackCoun`
- 结论：（无）
- 结果行数：183
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 10. `ec-025`（ecommerce_a3）
- 问题：查询现价高于其所属分类平均价格的商品，返回商品名称和现价两列，按商品编号升序。
- SQL：`WITH category_avg AS (SELECT category_id, AVG(price) AS avg_price FROM products GROUP BY category_id) SELECT p.name, p.price FROM products AS p JOIN category_avg AS ca ON p.category_id = ca.category_i`
- 结论：（无）
- 结果行数：100
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 11. `ch-019`（chinook_a3）
- 问题：有多少位艺术家没有发行过任何专辑？
- SQL：`SELECT COUNT(*) FROM Artist a WHERE NOT EXISTS (SELECT 1 FROM Album al WHERE al.ArtistId = a.ArtistId)`
- 结论：（无）
- 结果行数：1
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 12. `ec-002`（ecommerce_a3）
- 问题：统计每个一级分类（parent_id 为空的分类）下在售商品的数量，按数量降序；用分类名输出。
- SQL：`SELECT c.name AS category_name, COUNT(p.product_id) AS on_sale_product_count FROM categories c LEFT JOIN products p ON p.category_id = c.category_id AND p.status = 'on' WHERE c.parent_id IS NULL GROUP`
- 结论：（无）
- 结果行数：3
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 13. `sa-018`（sakila_a3）
- 问题：Which categories have an average film length above the overall average film length? Return category name and average length (1 decimal), ordered by average length descending, then category name.
- SQL：`WITH overall_avg AS (SELECT AVG(length) AS avg_len FROM film), category_avg AS (SELECT c.name AS category_name, AVG(f.length) AS avg_len FROM film f JOIN film_category fc ON f.film_id = fc.film_id JOI`
- 结论：（无）
- 结果行数：5
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 14. `sa-002`（sakila_a3）
- 问题：每个国家客户的支付总额，取前 5 名。金额相同按国家名升序。
- SQL：`SELECT c.country, SUM(p.amount) AS total_payment FROM payment AS p JOIN customer AS cu ON p.customer_id = cu.customer_id JOIN address AS a ON cu.address_id = a.address_id JOIN city AS ci ON a.city_id `
- 结论：（无）
- 结果行数：5
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 15. `ch-026`（chinook_a3）
- 问题：有多少位客户在 2025 年没有任何消费记录（发票）？
- SQL：`SELECT COUNT(*) FROM Customer c WHERE NOT EXISTS (SELECT 1 FROM Invoice i WHERE i.CustomerId = c.CustomerId AND i.InvoiceDate >= '2025-01-01' AND i.InvoiceDate < '2026-01-01');`
- 结论：（无）
- 结果行数：1
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 16. `ec-024`（ecommerce_a3）
- 问题：查询从未获得过 5 星评价的商品名称，按商品编号升序。
- SQL：`SELECT p.name FROM products p WHERE NOT EXISTS (SELECT 1 FROM reviews r WHERE r.product_id = p.product_id AND r.rating = 5) ORDER BY p.product_id ASC;`
- 结论：（无）
- 结果行数：60
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 17. `sa-008`（sakila_a3）
- 问题：每个电影类别各有多少部影片，占全部影片（1000 部）的百分比是多少（保留 1 位小数）？按影片数量从高到低排列，数量相同按类别名升序。
- SQL：`SELECT c.name AS category, COUNT(DISTINCT fc.film_id) AS film_count, ROUND(COUNT(DISTINCT fc.film_id) * 100.0 / 1000, 1) AS percentage FROM category AS c LEFT JOIN film_category AS fc ON c.category_id`
- 结论：（无）
- 结果行数：16
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 18. `ec-014`（ecommerce_a3）
- 问题：列出成交订单中下单金额（payments.amount）最高的前 50 笔，返回订单编号、用户名、支付金额三列，按金额降序。
- SQL：`SELECT o.order_id, u.username, SUM(p.amount) AS payment_amount FROM orders o JOIN users u ON o.user_id = u.user_id JOIN payments p ON p.order_id = o.order_id WHERE o.status IN ('paid', 'shipped', 'com`
- 结论：（无）
- 结果行数：50
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 19. `ec-008`（ecommerce_a3）
- 问题：计算每个城市的成交额占全库总 GMV 的百分比，返回城市和占比（百分比数值，保留两位小数）两列，按占比降序。
- SQL：`WITH completed_payments AS (SELECT o.user_id, p.amount FROM orders AS o JOIN payments AS p ON p.order_id = o.order_id WHERE o.status IN ('paid','shipped','completed')), city_gmv AS (SELECT u.city, SUM`
- 结论：（无）
- 结果行数：6
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 20. `ec-037`（ecommerce_a3）
- 问题：统计每个用户的成交订单数，用 RANK 按订单数降序排名，返回订单数排名第 1 的用户（若并列取用户编号最小者）的用户编号和订单数。
- SQL：`WITH user_order_counts AS (SELECT u.user_id, COUNT(o.order_id) AS order_count FROM users AS u LEFT JOIN orders AS o ON o.user_id = u.user_id AND o.status IN ('paid', 'shipped', 'completed') GROUP BY u`
- 结论：（无）
- 结果行数：1
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 21. `sa-004`（sakila_a3）
- 问题：List the first name, last name, and email of all active customers whose last name starts with 'S'. Order by last name, then first name.
- SQL：`SELECT first_name, last_name, email FROM customer WHERE active = '1' AND last_name LIKE 'S%' ORDER BY last_name, first_name;`
- 结论：（无）
- 结果行数：54
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 22. `sa-007`（sakila_a3）
- 问题：For each film rating, report the number of films and the average length in minutes (rounded to 1 decimal). Order by film count descending, then rating ascending.
- SQL：`SELECT rating, COUNT(film_id) AS film_count, ROUND(AVG(length), 1) AS average_length FROM film GROUP BY rating ORDER BY film_count DESC, rating ASC;`
- 结论：（无）
- 结果行数：5
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 23. `ch-018`（chinook_a3）
- 问题：按专辑数量给艺术家排名（专辑数相同给相同名次），返回排名、艺术家名和专辑数，取前 5 名，名次相同按艺术家名升序。
- SQL：`WITH artist_album_count AS (SELECT a.Name AS artist_name, COUNT(al.AlbumId) AS album_count FROM Artist a LEFT JOIN Album al ON a.ArtistId = al.ArtistId GROUP BY a.ArtistId, a.Name), ranked AS (SELECT `
- 结论：（无）
- 结果行数：5
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 24. `ec-012`（ecommerce_a3）
- 问题：计算每个支付方式（method）的成交额占全库总 GMV 的百分比，返回支付方式和百分比数值（保留两位小数）两列，按占比降序。
- SQL：`WITH paid_payments AS (SELECT p.method, p.amount FROM payments AS p JOIN orders AS o ON p.order_id = o.order_id WHERE o.status IN ('paid', 'shipped', 'completed')), totals AS (SELECT SUM(amount) AS to`
- 结论：（无）
- 结果行数：3
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 25. `ec-033`（ecommerce_a3）
- 问题：找出每个用户的第一笔成交订单（按时间最早），返回首笔订单金额最高的前 5 名用户的用户名和首笔金额，按金额降序。
- SQL：`WITH first_orders AS (SELECT o.user_id, o.order_id, ROW_NUMBER() OVER (PARTITION BY o.user_id ORDER BY o.created_at ASC, o.order_id ASC) AS rn FROM orders o WHERE o.status IN ('paid','shipped','comple`
- 结论：（无）
- 结果行数：5
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 26. `ec-027`（ecommerce_a3）
- 问题：用 WITH 找出成交订单数最多的一名用户，返回用户编号和成交订单数两列。
- SQL：`WITH user_counts AS (SELECT user_id, COUNT(*) AS transaction_orders FROM orders WHERE status IN ('paid', 'shipped', 'completed') GROUP BY user_id) SELECT user_id AS "用户编号", transaction_orders AS "成交订单`
- 结论：（无）
- 结果行数：1
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 27. `ec-043`（ecommerce_a3）
- 问题：统计成交订单中使用过 2 种及以上不同支付方式（method）的用户数量，返回单个数值。
- SQL：`SELECT COUNT(*) FROM (SELECT o.user_id FROM orders o JOIN payments p ON o.order_id = p.order_id WHERE o.status IN ('paid','shipped','completed') GROUP BY o.user_id HAVING COUNT(DISTINCT p.method) >= 2`
- 结论：（无）
- 结果行数：1
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 28. `ec-017`（ecommerce_a3）
- 问题：查询评分（rating）为 5 的评价，返回对应商品名称和评价内容两列，取前 50 条，按评价编号升序。
- SQL：`SELECT p.name, r.content FROM reviews r JOIN products p ON r.product_id = p.product_id WHERE r.rating = 5 ORDER BY r.review_id ASC LIMIT 50`
- 结论：（无）
- 结果行数：50
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 29. `sa-010`（sakila_a3）
- 问题：For each day with payments in July 2005, report the total revenue and the change versus the previous day with payments (current minus previous, 2 decimals; NULL for the first day). Output the day as 'YYYY-MM-DD', ordered chronologically.
- SQL：`WITH daily AS (SELECT strftime('%Y-%m-%d', payment_date) AS day, SUM(amount) AS total_revenue FROM payment WHERE strftime('%Y-%m', payment_date) = '2005-07' GROUP BY day) SELECT day, ROUND(total_reven`
- 结论：（无）
- 结果行数：14
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 30. `ec-034`（ecommerce_a3）
- 问题：按成交快照口径（order_items.unit_price × quantity）计算每个商品的成交额，用 RANK 排名，返回成交额最高的前 5 个商品的商品编号和成交额（保留两位小数），按排名升序。
- SQL：`WITH product_sales AS (SELECT oi.product_id AS product_id, SUM(oi.quantity * oi.unit_price) AS sales_amount FROM order_items oi JOIN orders o ON oi.order_id = o.order_id WHERE o.status IN ('paid','shi`
- 结论：（无）
- 结果行数：5
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：
