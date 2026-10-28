# 错误自信率人工评审表

口径：结论文本做出结果集不支持的断言即计一次（相关当因果 / 样本当全体 / 忽略 NULL 或截断 / 编造单位与趋势）。

## 1. `ch-014`（a2_chinook_v3）
- 问题：有多少位客户来自捷克共和国？
- SQL：`SELECT COUNT(CustomerId) FROM Customer WHERE Country = 'Czech Republic'`
- 结果行数：1
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 2. `sa-017`（a2_sakila_v3）
- 问题：有多少位已停用（非活跃）的客户仍然存在付款记录？
- SQL：`SELECT COUNT(DISTINCT c.customer_id) FROM customer c JOIN payment p ON c.customer_id = p.customer_id WHERE c.active = '0'`
- 结果行数：1
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 3. `ch-012`（a2_chinook_v3）
- 问题：2003 年入职的员工有哪几位？返回名字、姓氏和入职日期，按入职日期排序，同日按姓氏排序。
- SQL：`SELECT FirstName, LastName, HireDate FROM Employee WHERE strftime('%Y', HireDate) = '2003' ORDER BY HireDate, LastName`
- 结果行数：3
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 4. `sa-011`（a2_sakila_v3）
- 问题：How much revenue did each staff member handle, and what percentage of total revenue does each account for (1 decimal)? Return first name, last name, total amount, and percentage, ordered by total descending.
- SQL：`WITH staff_revenue AS (SELECT s.staff_id, s.first_name, s.last_name, COALESCE(SUM(p.amount), 0.0) AS total_amount FROM staff AS s LEFT JOIN payment AS p ON p.staff_id = s.staff_id GROUP BY s.staff_id,`
- 结果行数：2
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 5. `sa-003`（a2_sakila_v3）
- 问题：租借次数超过其所属类别平均租借次数的电影，返回电影标题，按标题升序排列，只取前 20 部。
- SQL：`WITH rental_counts AS (SELECT f.film_id, COUNT(r.rental_id) AS rental_count FROM film f LEFT JOIN inventory i ON f.film_id = i.film_id LEFT JOIN rental r ON i.inventory_id = r.inventory_id GROUP BY f.`
- 结果行数：20
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 6. `sa-009`（a2_sakila_v3）
- 问题：Rank customers by their total payment amount (ties share the same rank). Return rank, first name, last name, and total amount for the top 5; break ties by last name ascending.
- SQL：`WITH customer_totals AS (SELECT c.customer_id, c.first_name, c.last_name, SUM(p.amount) AS total_amount FROM customer c JOIN payment p ON p.customer_id = c.customer_id GROUP BY c.customer_id, c.first_`
- 结果行数：5
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 7. `ch-015`（a2_chinook_v3）
- 问题：每个国家的客户数量及其占总客户数的百分比（保留 1 位小数），按客户数量从高到低排列，数量相同按国家名升序。
- SQL：`SELECT Country, COUNT(*) AS CustomerCount, ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM Customer), 1) AS Percentage FROM Customer GROUP BY Country ORDER BY CustomerCount DESC, Country ASC;`
- 结果行数：24
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 8. `ch-006`（a2_chinook_v3）
- 问题：2025 年 1 月的发票总额是多少？
- SQL：`SELECT SUM(Total) FROM Invoice WHERE InvoiceDate >= '2025-01-01' AND InvoiceDate < '2025-02-01';`
- 结果行数：1
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 9. `sa-007`（a2_sakila_v3）
- 问题：For each film rating, report the number of films and the average length in minutes (rounded to 1 decimal). Order by film count descending, then rating ascending.
- SQL：`SELECT rating, COUNT(*) AS film_count, ROUND(AVG(length), 1) AS avg_length_minutes FROM film GROUP BY rating ORDER BY film_count DESC, rating ASC;`
- 结果行数：5
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 10. `sa-010`（a2_sakila_v3）
- 问题：For each day with payments in July 2005, report the total revenue and the change versus the previous day with payments (current minus previous, 2 decimals; NULL for the first day). Output the day as 'YYYY-MM-DD', ordered chronologically.
- SQL：`WITH daily AS (SELECT date(payment_date) AS day, SUM(amount) AS total_revenue FROM payment WHERE date(payment_date) BETWEEN '2005-07-01' AND '2005-07-31' GROUP BY date(payment_date)) SELECT day, ROUND`
- 结果行数：14
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 11. `sa-004`（a2_sakila_v3）
- 问题：List the first name, last name, and email of all active customers whose last name starts with 'S'. Order by last name, then first name.
- SQL：`SELECT first_name, last_name, email FROM customer WHERE CAST(active AS TEXT) IN ('Y', '1', 'TRUE', 'true') AND last_name LIKE 'S%' ORDER BY last_name, first_name`
- 结果行数：54
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 12. `ch-005`（a2_chinook_v3）
- 问题：消费总额最高的 5 位客户，返回他们的名、姓和累计消费金额。金额相同按姓氏升序，再按名升序。
- SQL：`SELECT c.FirstName, c.LastName, SUM(i.Total) AS TotalSpent FROM Customer c JOIN Invoice i ON c.CustomerId = i.CustomerId GROUP BY c.CustomerId, c.FirstName, c.LastName ORDER BY TotalSpent DESC, c.Last`
- 结果行数：5
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 13. `ch-013`（a2_chinook_v3）
- 问题：列出时长在 10 分钟以上（含）的曲目中时长最长的 10 首，返回曲目名称和时长（以毫秒为单位），按时长从高到低排列，时长相同按曲目名升序。
- SQL：`SELECT Name, Milliseconds FROM Track WHERE Milliseconds >= 600000 ORDER BY Milliseconds DESC, Name ASC LIMIT 10`
- 结果行数：10
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 14. `ch-026`（a2_chinook_v3）
- 问题：有多少位客户在 2025 年没有任何消费记录（发票）？
- SQL：`SELECT COUNT(*) FROM Customer AS c WHERE NOT EXISTS (SELECT 1 FROM Invoice AS i WHERE i.CustomerId = c.CustomerId AND strftime('%Y', i.InvoiceDate) = '2025');`
- 结果行数：1
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 15. `ch-004`（a2_chinook_v3）
- 问题：哪些专辑的总时长超过 60 分钟？按专辑标题字母序排列。
- SQL：`SELECT a.Title FROM Album AS a JOIN Track AS t ON a.AlbumId = t.AlbumId GROUP BY a.AlbumId, a.Title HAVING SUM(t.Milliseconds) > 3600000 ORDER BY a.Title`
- 结果行数：102
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 16. `sa-006`（a2_sakila_v3）
- 问题：How many films include 'Deleted Scenes' among their special features?
- SQL：`SELECT COUNT(*) FROM film WHERE special_features LIKE '%Deleted Scenes%';`
- 结果行数：1
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 17. `ch-023`（a2_chinook_v3）
- 问题：找出消费总额高于其所在国家客户平均消费额的客户，返回名、姓和消费总额，按消费总额从高到低排列，金额相同按姓氏升序。
- SQL：`WITH customer_spend AS (SELECT c.CustomerId, c.FirstName, c.LastName, c.Country, COALESCE(SUM(i.Total), 0) AS TotalSpent FROM Customer AS c LEFT JOIN Invoice AS i ON c.CustomerId = i.CustomerId GROUP `
- 结果行数：13
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 18. `sa-001`（a2_sakila_v3）
- 问题：评级为 NC-17 且时长超过 120 分钟的电影中，时长最长的 10 部是哪些？返回电影标题和时长（分钟），按时长从高到低排列，时长相同按标题升序。
- SQL：`SELECT title, length FROM film WHERE rating = 'NC-17' AND length > 120 ORDER BY length DESC, title ASC LIMIT 10;`
- 结果行数：10
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 19. `ch-017`（a2_chinook_v3）
- 问题：2025 年每个月的发票总额，以及该月相对上月的金额变化（本月总额 − 上月总额，保留 2 位小数；1 月为 NULL），月份按 'YYYY-MM' 格式输出，按月从早到晚排列。
- SQL：`WITH RECURSIVE months AS (SELECT '2025-01' AS month UNION ALL SELECT strftime('%Y-%m', date(month || '-01', '+1 month')) FROM months WHERE month < '2025-12'), monthly_totals AS (SELECT months.month AS`
- 结果行数：12
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 20. `sa-015`（a2_sakila_v3）
- 问题：出演过动作片（Action 类别）的演员中，出演动作片数量最多的前 5 位是谁？返回名、姓和动作片数量，按数量从高到低排列，数量相同按姓升序、再按名升序。
- SQL：`SELECT a.first_name, a.last_name, COUNT(DISTINCT fa.film_id) AS action_film_count FROM actor a JOIN film_actor fa ON a.actor_id = fa.actor_id JOIN film_category fc ON fa.film_id = fc.film_id JOIN cate`
- 结果行数：5
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 21. `sa-012`（a2_sakila_v3）
- 问题：Which actors appeared in more than 30 films? Return first name, last name, and film count, ordered by count descending, then last name, then first name.
- SQL：`SELECT a.first_name, a.last_name, COUNT(fa.film_id) AS film_count FROM actor AS a JOIN film_actor AS fa ON a.actor_id = fa.actor_id GROUP BY a.actor_id, a.first_name, a.last_name HAVING COUNT(fa.film_`
- 结果行数：56
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 22. `sa-002`（a2_sakila_v3）
- 问题：每个国家客户的支付总额，取前 5 名。金额相同按国家名升序。
- SQL：`SELECT c.country, COALESCE(SUM(p.amount), 0) AS total_payment FROM country AS c LEFT JOIN city AS ci ON c.country_id = ci.country_id LEFT JOIN address AS a ON ci.city_id = a.city_id LEFT JOIN customer`
- 结果行数：5
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 23. `ch-001`（a2_chinook_v3）
- 问题：列出所有巴西客户的姓名和邮箱。要求返回两列：完整姓名（名与姓之间用空格拼接）和邮箱。
- SQL：`SELECT FirstName || ' ' || LastName AS Full_Name, Email FROM Customer WHERE Country = 'Brazil';`
- 结果行数：5
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 24. `sa-018`（a2_sakila_v3）
- 问题：Which categories have an average film length above the overall average film length? Return category name and average length (1 decimal), ordered by average length descending, then category name.
- SQL：`WITH overall_avg AS (SELECT AVG(length) AS avg_length FROM film) SELECT c.name, ROUND(AVG(f.length), 1) AS average_length FROM film_category AS fc JOIN film AS f ON fc.film_id = f.film_id JOIN categor`
- 结果行数：5
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 25. `ch-019`（a2_chinook_v3）
- 问题：有多少位艺术家没有发行过任何专辑？
- SQL：`SELECT COUNT(*) FROM Artist WHERE NOT EXISTS (SELECT 1 FROM Album WHERE Album.ArtistId = Artist.ArtistId);`
- 结果行数：1
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 26. `ch-025`（a2_chinook_v3）
- 问题：曲目数量高于全部专辑平均曲目数量的专辑有哪些？返回专辑名和曲目数量，按曲目数量从高到低排列，数量相同按专辑名升序。
- SQL：`WITH album_track_counts AS (SELECT a.AlbumId, a.Title, COUNT(t.TrackId) AS TrackCount FROM Album AS a LEFT JOIN Track AS t ON a.AlbumId = t.AlbumId GROUP BY a.AlbumId, a.Title), avg_track_count AS (SE`
- 结果行数：183
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 27. `ch-003`（a2_chinook_v3）
- 问题：每个音乐流派的曲目数量，按数量从高到低排列，数量相同按流派名升序。
- SQL：`SELECT g.Name AS Genre, COUNT(t.TrackId) AS TrackCount FROM Genre AS g LEFT JOIN Track AS t ON g.GenreId = t.GenreId GROUP BY g.GenreId, g.Name ORDER BY TrackCount DESC, g.Name ASC`
- 结果行数：25
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 28. `sa-016`（a2_sakila_v3）
- 问题：Find films whose rental rate is above the average rental rate of films with the same rating. Return title, rating, and rental rate for the 10 with the highest rental rate; break ties by title ascending.
- SQL：`SELECT f.title, f.rating, f.rental_rate FROM film AS f WHERE f.rental_rate > (SELECT AVG(f2.rental_rate) FROM film AS f2 WHERE f2.rating IS f.rating) ORDER BY f.rental_rate DESC, f.title ASC LIMIT 10;`
- 结果行数：10
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 29. `sa-008`（a2_sakila_v3）
- 问题：每个电影类别各有多少部影片，占全部影片（1000 部）的百分比是多少（保留 1 位小数）？按影片数量从高到低排列，数量相同按类别名升序。
- SQL：`SELECT c.name AS category_name, COUNT(fc.film_id) AS film_count, ROUND(COUNT(fc.film_id) * 100.0 / 1000, 1) AS percentage FROM category AS c LEFT JOIN film_category AS fc ON c.category_id = fc.categor`
- 结果行数：16
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 30. `sa-005`（a2_sakila_v3）
- 问题：Which 5 films have the highest replacement cost? Return the title and replacement cost; break ties by title in ascending order.
- SQL：`SELECT title, replacement_cost FROM film ORDER BY replacement_cost DESC, title ASC LIMIT 5;`
- 结果行数：5
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：
