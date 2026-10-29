# 错误自信率人工评审表

口径：结论文本做出结果集不支持的断言即计一次（相关当因果 / 样本当全体 / 忽略 NULL 或截断 / 编造单位与趋势）。

## 1. `ec-021`（ecommerce_a3）
- 问题：查询每个商品的名称、分类名称、供应商名称三列，按商品编号升序。
- SQL：`SELECT p.name AS product_name, c.name AS category_name, s.name AS supplier_name FROM products AS p LEFT JOIN categories AS c ON p.category_id = c.category_id LEFT JOIN suppliers AS s ON p.supplier_id `
- 结果行数：200
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 2. `ch-026`（chinook_a3）
- 问题：有多少位客户在 2025 年没有任何消费记录（发票）？
- SQL：`SELECT COUNT(*) FROM Customer c WHERE NOT EXISTS (SELECT 1 FROM Invoice i WHERE i.CustomerId = c.CustomerId AND strftime('%Y', i.InvoiceDate) = '2025');`
- 结果行数：1
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 3. `sa-012`（sakila_a3）
- 问题：Which actors appeared in more than 30 films? Return first name, last name, and film count, ordered by count descending, then last name, then first name.
- SQL：`SELECT a.first_name, a.last_name, COUNT(fa.film_id) AS film_count FROM actor AS a JOIN film_actor AS fa ON a.actor_id = fa.actor_id GROUP BY a.actor_id, a.first_name, a.last_name HAVING COUNT(fa.film_`
- 结果行数：56
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 4. `ec-015`（ecommerce_a3）
- 问题：统计每个支付方式（method）的成交总金额，返回支付方式和总金额两列，按总金额降序。
- SQL：`SELECT p.method, SUM(p.amount) AS total_amount FROM payments AS p JOIN orders AS o ON p.order_id = o.order_id WHERE o.status IN ('paid','shipped','completed') GROUP BY p.method ORDER BY total_amount D`
- 结果行数：3
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 5. `ch-012`（chinook_a3）
- 问题：2003 年入职的员工有哪几位？返回名字、姓氏和入职日期，按入职日期排序，同日按姓氏排序。
- SQL：`SELECT FirstName, LastName, HireDate FROM Employee WHERE strftime('%Y', HireDate) = '2003' ORDER BY DATE(HireDate), LastName;`
- 结果行数：3
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 6. `ch-021`（chinook_a3）
- 问题：每位销售支持代理（Sales Support Agent）名下有多少位客户、这些客户的总消费金额是多少？返回姓氏、名字、客户数和总消费金额，按客户数从高到低排列，客户数相同按姓氏升序。
- SQL：`SELECT e.LastName, e.FirstName, COUNT(DISTINCT c.CustomerId) AS customer_count, COALESCE(SUM(i.Total), 0) AS total_spent FROM Employee AS e LEFT JOIN Customer AS c ON c.SupportRepId = e.EmployeeId LEF`
- 结果行数：3
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 7. `ch-020`（chinook_a3）
- 问题：有多少首曲目在 2024 年和 2025 年都出现在发票中（即两年都被售出过）？
- SQL：`SELECT COUNT(*) FROM (SELECT il.TrackId FROM InvoiceLine AS il JOIN Invoice AS i ON il.InvoiceId = i.InvoiceId WHERE strftime('%Y', i.InvoiceDate) IN ('2024', '2025') GROUP BY il.TrackId HAVING COUNT(`
- 结果行数：1
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 8. `sa-009`（sakila_a3）
- 问题：Rank customers by their total payment amount (ties share the same rank). Return rank, first name, last name, and total amount for the top 5; break ties by last name ascending.
- SQL：`WITH customer_totals AS (SELECT c.customer_id, c.first_name, c.last_name, COALESCE(SUM(p.amount), 0) AS total_amount FROM customer AS c LEFT JOIN payment AS p ON p.customer_id = c.customer_id GROUP BY`
- 结果行数：5
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 9. `ec-023`（ecommerce_a3）
- 问题：查询下过订单、但所有订单都处于取消（cancelled）或退款（refunded）状态的用户名，按用户编号升序。
- SQL：`SELECT u.username FROM users AS u WHERE EXISTS (SELECT 1 FROM orders AS o WHERE o.user_id = u.user_id) AND NOT EXISTS (SELECT 1 FROM orders AS o WHERE o.user_id = u.user_id AND (o.status NOT IN ('canc`
- 结果行数：5
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 10. `ch-005`（chinook_a3）
- 问题：消费总额最高的 5 位客户，返回他们的名、姓和累计消费金额。金额相同按姓氏升序，再按名升序。
- SQL：`SELECT c.FirstName, c.LastName, SUM(i.Total) AS TotalSpent FROM Customer c JOIN Invoice i ON c.CustomerId = i.CustomerId GROUP BY c.CustomerId, c.FirstName, c.LastName ORDER BY TotalSpent DESC, c.Last`
- 结果行数：5
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 11. `sa-015`（sakila_a3）
- 问题：出演过动作片（Action 类别）的演员中，出演动作片数量最多的前 5 位是谁？返回名、姓和动作片数量，按数量从高到低排列，数量相同按姓升序、再按名升序。
- SQL：`SELECT a.first_name, a.last_name, COUNT(DISTINCT fa.film_id) AS action_film_count FROM actor a JOIN film_actor fa ON a.actor_id = fa.actor_id JOIN film_category fc ON fa.film_id = fc.film_id JOIN cate`
- 结果行数：5
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 12. `ec-009`（ecommerce_a3）
- 问题：按成交快照口径（order_items.unit_price × quantity，而不是 products.price 现价）计算每个商品的成交销售额，返回销售额最高的前 5 个商品的商品编号和销售额（保留两位小数），按销售额降序。
- SQL：`SELECT oi.product_id, ROUND(SUM(oi.quantity * oi.unit_price), 2) AS sales_amount FROM order_items AS oi JOIN orders AS o ON oi.order_id = o.order_id WHERE o.status IN ('paid', 'shipped', 'completed') `
- 结果行数：5
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 13. `ec-011`（ecommerce_a3）
- 问题：统计每个供应商供应的商品数量，返回商品数最多的前 3 个供应商的名称和商品数两列，按商品数降序；商品数相同时按供应商编号升序。
- SQL：`SELECT s.name AS supplier_name, COUNT(p.product_id) AS product_count FROM suppliers AS s LEFT JOIN products AS p ON s.supplier_id = p.supplier_id GROUP BY s.supplier_id, s.name ORDER BY product_count `
- 结果行数：3
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 14. `ec-019`（ecommerce_a3）
- 问题：查询每个二级分类（parent_id 非空），返回二级分类名称和其父分类名称两列，按二级分类编号升序。
- SQL：`SELECT c.name AS category_name, p.name AS parent_name FROM categories c JOIN categories p ON c.parent_id = p.category_id WHERE c.parent_id IS NOT NULL ORDER BY c.category_id ASC`
- 结果行数：6
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 15. `ch-024`（chinook_a3）
- 问题：从未出现在任何发票中的曲目有多少首？
- SQL：`SELECT COUNT(*) FROM Track t WHERE NOT EXISTS (SELECT 1 FROM InvoiceLine il WHERE il.TrackId = t.TrackId)`
- 结果行数：1
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 16. `ec-027`（ecommerce_a3）
- 问题：用 WITH 找出成交订单数最多的一名用户，返回用户编号和成交订单数两列。
- SQL：`WITH user_counts AS (SELECT user_id, COUNT(*) AS transaction_orders FROM orders WHERE status IN ('paid', 'shipped', 'completed') GROUP BY user_id) SELECT user_id AS "用户编号", transaction_orders AS "成交订单`
- 结果行数：1
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 17. `sa-010`（sakila_a3）
- 问题：For each day with payments in July 2005, report the total revenue and the change versus the previous day with payments (current minus previous, 2 decimals; NULL for the first day). Output the day as 'YYYY-MM-DD', ordered chronologically.
- SQL：`WITH daily AS (SELECT DATE(payment_date) AS day, SUM(amount) AS total_revenue FROM payment WHERE DATE(payment_date) BETWEEN '2005-07-01' AND '2005-07-31' GROUP BY DATE(payment_date)) SELECT day AS "da`
- 结果行数：14
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 18. `ec-018`（ecommerce_a3）
- 问题：列出使用过优惠券的订单中支付金额最高的前 50 个，返回订单编号、优惠券编码、折扣率三列，按支付金额降序；金额相同时按订单编号升序。
- SQL：`SELECT o.order_id, c.code, c.discount_pct FROM orders o JOIN coupons c ON c.coupon_id = o.coupon_id JOIN payments p ON p.order_id = o.order_id WHERE o.coupon_id IS NOT NULL AND o.status IN ('paid','sh`
- 结果行数：50
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 19. `ec-039`（ecommerce_a3）
- 问题：计算每个成交用户相邻两笔成交订单之间的下单间隔天数，返回全库最大的间隔天数（整数），返回单个数值。
- SQL：`WITH paid_orders AS (SELECT user_id, created_at, LAG(created_at) OVER (PARTITION BY user_id ORDER BY created_at) AS prev_created_at FROM orders WHERE status IN ('paid','shipped','completed') AND user_`
- 结果行数：1
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 20. `ec-031`（ecommerce_a3）
- 问题：用 WITH 计算每个用户的成交总额，返回累计消费最高的前 5 名用户（用户名和累计金额），按金额降序。
- SQL：`WITH user_gmv AS (SELECT o.user_id, SUM(p.amount) AS total_amount FROM orders o JOIN payments p ON p.order_id = o.order_id WHERE o.status IN ('paid','shipped','completed') GROUP BY o.user_id) SELECT u`
- 结果行数：5
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 21. `ec-020`（ecommerce_a3）
- 问题：统计每个城市的成交总金额（GMV 口径），返回城市和总金额两列，按总金额降序。
- SQL：`SELECT u.city AS city, SUM(p.amount) AS total_gmv FROM orders AS o JOIN users AS u ON o.user_id = u.user_id JOIN payments AS p ON p.order_id = o.order_id WHERE o.status IN ('paid', 'shipped', 'complet`
- 结果行数：6
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 22. `ec-043`（ecommerce_a3）
- 问题：统计成交订单中使用过 2 种及以上不同支付方式（method）的用户数量，返回单个数值。
- SQL：`SELECT COUNT(*) FROM (SELECT o.user_id FROM orders o JOIN payments p ON o.order_id = p.order_id WHERE o.status IN ('paid','shipped','completed') GROUP BY o.user_id HAVING COUNT(DISTINCT p.method) >= 2`
- 结果行数：1
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 23. `ec-004`（ecommerce_a3）
- 问题：统计每个商品的评价数量，取评价数最多的前 13 个商品，返回商品编号和评价数两列，按评价数降序。
- SQL：`SELECT p.product_id, COUNT(r.review_id) AS review_count FROM products AS p LEFT JOIN reviews AS r ON r.product_id = p.product_id GROUP BY p.product_id ORDER BY review_count DESC, p.product_id ASC LIMI`
- 结果行数：13
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 24. `ec-017`（ecommerce_a3）
- 问题：查询评分（rating）为 5 的评价，返回对应商品名称和评价内容两列，取前 50 条，按评价编号升序。
- SQL：`SELECT p.name, r.content FROM reviews r JOIN products p ON r.product_id = p.product_id WHERE r.rating = 5 ORDER BY r.review_id ASC LIMIT 50`
- 结果行数：50
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 25. `sa-006`（sakila_a3）
- 问题：How many films include 'Deleted Scenes' among their special features?
- SQL：`SELECT COUNT(*) AS film_count FROM film WHERE special_features LIKE '%Deleted Scenes%'`
- 结果行数：1
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 26. `ec-025`（ecommerce_a3）
- 问题：查询现价高于其所属分类平均价格的商品，返回商品名称和现价两列，按商品编号升序。
- SQL：`WITH category_avg AS (SELECT category_id, AVG(price) AS avg_price FROM products GROUP BY category_id) SELECT p.name, p.price FROM products AS p JOIN category_avg AS ca ON p.category_id = ca.category_i`
- 结果行数：100
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 27. `sa-002`（sakila_a3）
- 问题：每个国家客户的支付总额，取前 5 名。金额相同按国家名升序。
- SQL：`SELECT c.country, SUM(p.amount) AS total_payment FROM payment AS p JOIN customer AS cu ON p.customer_id = cu.customer_id JOIN address AS a ON cu.address_id = a.address_id JOIN city AS ci ON a.city_id `
- 结果行数：5
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 28. `ch-013`（chinook_a3）
- 问题：列出时长在 10 分钟以上（含）的曲目中时长最长的 10 首，返回曲目名称和时长（以毫秒为单位），按时长从高到低排列，时长相同按曲目名升序。
- SQL：`SELECT Name, Milliseconds FROM Track WHERE Milliseconds >= 600000 ORDER BY Milliseconds DESC, Name ASC LIMIT 10`
- 结果行数：10
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 29. `ch-025`（chinook_a3）
- 问题：曲目数量高于全部专辑平均曲目数量的专辑有哪些？返回专辑名和曲目数量，按曲目数量从高到低排列，数量相同按专辑名升序。
- SQL：`WITH album_track_counts AS (SELECT a.AlbumId, a.Title, COUNT(t.TrackId) AS track_count FROM Album a LEFT JOIN Track t ON t.AlbumId = a.AlbumId GROUP BY a.AlbumId, a.Title), avg_count AS (SELECT AVG(tr`
- 结果行数：183
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 30. `ec-034`（ecommerce_a3）
- 问题：按成交快照口径（order_items.unit_price × quantity）计算每个商品的成交额，用 RANK 排名，返回成交额最高的前 5 个商品的商品编号和成交额（保留两位小数），按排名升序。
- SQL：`WITH product_sales AS (SELECT oi.product_id AS product_id, SUM(oi.quantity * oi.unit_price) AS sales_amount FROM order_items oi JOIN orders o ON oi.order_id = o.order_id WHERE o.status IN ('paid','shi`
- 结果行数：5
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：
