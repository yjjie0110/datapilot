# 错误自信率人工评审表

口径：结论文本做出结果集不支持的断言即计一次（相关当因果 / 样本当全体 / 忽略 NULL 或截断 / 编造单位与趋势）。

## 1. `ec-021`（v2_ecommerce_a3）
- 问题：查询每个商品的名称、分类名称、供应商名称三列，按商品编号升序。
- SQL：`SELECT p.name AS product_name, c.name AS category_name, s.name AS supplier_name FROM products AS p LEFT JOIN categories AS c ON p.category_id = c.category_id LEFT JOIN suppliers AS s ON p.supplier_id `
- 结论：共200行，按商品编号升序展示前10行商品名称、分类名称、供应商名称；商品001为洗衣机、供应商Q，商品010为家电、供应商T。
- 结果行数：200
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 2. `ch-026`（v2_chinook_a3）
- 问题：有多少位客户在 2025 年没有任何消费记录（发票）？
- SQL：`SELECT COUNT(*) AS customer_count FROM Customer AS c WHERE NOT EXISTS (SELECT 1 FROM Invoice AS i WHERE i.CustomerId = c.CustomerId AND strftime('%Y', i.InvoiceDate) = '2025');`
- 结论：共有13位客户在2025年没有任何消费记录（发票）。
- 结果行数：1
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 3. `sa-015`（v2_sakila_a3）
- 问题：出演过动作片（Action 类别）的演员中，出演动作片数量最多的前 5 位是谁？返回名、姓和动作片数量，按数量从高到低排列，数量相同按姓升序、再按名升序。
- SQL：`WITH action_counts AS (SELECT fa.actor_id, COUNT(DISTINCT fa.film_id) AS action_count FROM film_actor AS fa JOIN film_category AS fc ON fa.film_id = fc.film_id JOIN category AS c ON fc.category_id = c`
- 结论：动作片数量最多的前5位演员为NATALIE HOPKINS（6部），以及KIRSTEN AKROYD、JON CHASE、AL GARLAND、SEAN GUINESS（各5部）。
- 结果行数：5
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 4. `ec-016`（v2_ecommerce_a3）
- 问题：统计每个商品在成交订单中被购买的总数量（order_items.quantity 求和），返回总量最多的前 25 个商品（商品编号和总量），按总量降序。
- SQL：`WITH product_sales AS (SELECT oi.product_id, SUM(oi.quantity) AS total_quantity FROM order_items oi JOIN orders o ON oi.order_id = o.order_id WHERE o.status IN ('paid', 'shipped', 'completed') GROUP B`
- 结论：成交订单中购买总量最多的前25商品（展示前10行）：商品104以89居首，23、7、119分别为84、83、83。
- 结果行数：25
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 5. `ch-014`（v2_chinook_a3）
- 问题：有多少位客户来自捷克共和国？
- SQL：`SELECT COUNT(*) FROM Customer WHERE Country = 'Czech Republic';`
- 结论：有2位客户来自捷克共和国。
- 结果行数：1
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 6. `sa-002`（v2_sakila_a3）
- 问题：每个国家客户的支付总额，取前 5 名。金额相同按国家名升序。
- SQL：`WITH country_payment AS (SELECT c.country, SUM(p.amount) AS total_amount FROM payment p JOIN customer cu ON p.customer_id = cu.customer_id JOIN address a ON cu.address_id = a.address_id JOIN city ci O`
- 结论：国家客户支付总额前5名依次为：India 6630.27、China 5802.73、United States 4110.32、Japan 3471.74、Mexico 3307.04。
- 结果行数：5
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 7. `ch-024`（v2_chinook_a3）
- 问题：从未出现在任何发票中的曲目有多少首？
- SQL：`SELECT COUNT(*) FROM Track AS t WHERE NOT EXISTS (SELECT 1 FROM InvoiceLine AS il WHERE il.TrackId = t.TrackId)`
- 结论：从未出现在任何发票中的曲目共有1519首。
- 结果行数：1
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 8. `ec-001`（v2_ecommerce_a3）
- 问题：查询所有在售（status=on）且现价高于 500 的商品，返回商品名称和现价两列，按现价降序；价格相同时按商品编号升序。
- SQL：`SELECT name, price FROM products WHERE status = 'on' AND price > 500 ORDER BY price DESC, product_id ASC;`
- 结论：在售且现价高于500的商品共89行，前10行中商品141现价996.73最高，商品067现价958.74最低。
- 结果行数：89
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 9. `ec-023`（v2_ecommerce_a3）
- 问题：查询下过订单、但所有订单都处于取消（cancelled）或退款（refunded）状态的用户名，按用户编号升序。
- SQL：`SELECT u.username FROM users u WHERE EXISTS (SELECT 1 FROM orders o WHERE o.user_id = u.user_id) AND NOT EXISTS (SELECT 1 FROM orders o WHERE o.user_id = u.user_id AND (o.status IS NULL OR o.status NO`
- 结论：按用户编号升序，下过订单且所有订单均为取消或退款状态的用户名为 user065、user169、user271、user297、user395。
- 结果行数：5
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 10. `ch-010`（v2_chinook_a3）
- 问题：列出所有姓 Smith 的客户的姓名和邮箱。
- SQL：`SELECT FirstName, LastName, Email FROM Customer WHERE LastName = 'Smith'`
- 结论：姓 Smith 的客户为 Jack Smith，邮箱是 jacksmith@microsoft.com。
- 结果行数：1
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 11. `ec-006`（v2_ecommerce_a3）
- 问题：计算 GMV：即成交订单（paid/shipped/completed）在 payments 表的 amount 求和，保留两位小数，返回单个数值。
- SQL：`SELECT ROUND(SUM(p.amount), 2) AS gmv FROM payments AS p JOIN orders AS o ON p.order_id = o.order_id WHERE o.status IN ('paid', 'shipped', 'completed');`
- 结论：成交订单（paid、shipped、completed）对应的GMV为5546447.94。
- 结果行数：1
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 12. `ec-013`（v2_ecommerce_a3）
- 问题：找出成交订单数最多的前 15 名用户，返回用户编号和成交订单数两列，按订单数降序。
- SQL：`WITH user_order_counts AS (SELECT user_id, COUNT(*) AS order_count FROM orders WHERE status IN ('paid','shipped','completed') AND user_id IS NOT NULL GROUP BY user_id), ranked AS (SELECT user_id, orde`
- 结论：展示前10行：用户310成交订单数13最高，用户235、421各12，用户91、250各11，用户80、232、255、268、299各10。
- 结果行数：15
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 13. `ec-012`（v2_ecommerce_a3）
- 问题：计算每个支付方式（method）的成交额占全库总 GMV 的百分比，返回支付方式和百分比数值（保留两位小数）两列，按占比降序。
- SQL：`WITH total_gmv AS (
  SELECT SUM(p.amount) AS total_amount
  FROM payments p
  JOIN orders o ON o.order_id = p.order_id
  WHERE o.status IN ('paid','shipped','completed')
  ),
  method_gmv AS (
  SELECT p`
- 结论：按占比降序，card、alipay和wechat三种支付方式的成交额占比分别为34.58%、33.18%和32.24%。
- 结果行数：3
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 14. `ec-019`（v2_ecommerce_a3）
- 问题：查询每个二级分类（parent_id 非空），返回二级分类名称和其父分类名称两列，按二级分类编号升序。
- SQL：`SELECT c.name AS category_name, p.name AS parent_name FROM categories AS c JOIN categories AS p ON c.parent_id = p.category_id WHERE c.parent_id IS NOT NULL ORDER BY c.category_id ASC;`
- 结论：按二级分类编号升序，手机、耳机的父分类为数码；冰箱、洗衣机的父分类为家电；男装、女装的父分类为服饰。
- 结果行数：6
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 15. `ch-025`（v2_chinook_a3）
- 问题：曲目数量高于全部专辑平均曲目数量的专辑有哪些？返回专辑名和曲目数量，按曲目数量从高到低排列，数量相同按专辑名升序。
- SQL：`WITH album_counts AS (
  SELECT
    a.AlbumId,
    a.Title,
    COUNT(t.TrackId) AS track_count
  FROM Album a
  LEFT JOIN Track t ON a.AlbumId = t.AlbumId
  GROUP BY a.AlbumId, a.Title
  ),
  avg_count A`
- 结论：曲目数高于平均的专辑共183张，前10名包括 Greatest Hits(57)、Minha Historia(34)、Unplugged(30)等。
- 结果行数：183
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 16. `ec-028`（v2_ecommerce_a3）
- 问题：用 WITH 统计每个城市的成交订单数，返回成交订单数最多的城市及其订单数两列。
- SQL：`WITH city_orders AS (
  SELECT u.city, COUNT(o.order_id) AS order_count
  FROM orders AS o
  JOIN users AS u ON o.user_id = u.user_id
  WHERE o.status IN ('paid', 'shipped', 'completed')
  GROUP BY u.`
- 结论：成交订单数最多的城市为北京，订单数为436。
- 结果行数：1
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 17. `sa-017`（v2_sakila_a3）
- 问题：有多少位已停用（非活跃）的客户仍然存在付款记录？
- SQL：`SELECT COUNT(DISTINCT p.customer_id) FROM payment AS p JOIN customer AS c ON c.customer_id = p.customer_id WHERE c.active = '0';`
- 结论：共有15位已停用（非活跃）客户仍存在付款记录。
- 结果行数：1
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 18. `ec-027`（v2_ecommerce_a3）
- 问题：用 WITH 找出成交订单数最多的一名用户，返回用户编号和成交订单数两列。
- SQL：`WITH deal_orders AS (SELECT user_id, COUNT(*) AS order_count FROM orders WHERE status IN ('paid', 'shipped', 'completed') GROUP BY user_id), ranked AS (SELECT user_id, order_count, ROW_NUMBER() OVER (`
- 结论：成交订单数最多的用户编号为310，成交订单数为13。
- 结果行数：1
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 19. `ec-040`（v2_ecommerce_a3）
- 问题：统计每个用户通过优惠券兑换中间表（coupon_redemptions）兑换优惠券的次数，返回兑换次数最多的前 5 名用户的用户名和兑换次数两列，按兑换次数降序；次数相同时按用户编号升序。
- SQL：`WITH user_redemption_counts AS (
  SELECT
    cr.user_id,
    u.username,
    COUNT(*) AS redemption_count
  FROM coupon_redemptions AS cr
  JOIN users AS u ON u.user_id = cr.user_id
  GROUP BY cr.use`
- 结论：兑换次数最多的前5名用户为user421（6次）、user146（4次）、user255（4次）、user299（4次）、user310（4次）。
- 结果行数：5
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 20. `ec-034`（v2_ecommerce_a3）
- 问题：按成交快照口径（order_items.unit_price × quantity）计算每个商品的成交额，用 RANK 排名，返回成交额最高的前 5 个商品的商品编号和成交额（保留两位小数），按排名升序。
- SQL：`WITH product_sales AS (SELECT oi.product_id, SUM(oi.unit_price * oi.quantity) AS sales_amount FROM order_items AS oi JOIN orders AS o ON o.order_id = oi.order_id WHERE o.status IN ('paid', 'shipped', `
- 结论：成交额最高的前5个商品依次为36（71320.86）、141（69771.10）、81（68720.10）、198（68418.33）、7（67275.65）。
- 结果行数：5
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 21. `ec-020`（v2_ecommerce_a3）
- 问题：统计每个城市的成交总金额（GMV 口径），返回城市和总金额两列，按总金额降序。
- SQL：`SELECT u.city AS city, SUM(p.amount) AS total_gmv FROM orders o JOIN users u ON o.user_id = u.user_id JOIN payments p ON p.order_id = o.order_id WHERE o.status IN ('paid','shipped','completed') GROUP `
- 结论：GMV降序：北京1065925.0、深圳1000622.5、None897835.74、成都879827.77、杭州873417.91、上海828819.02
- 结果行数：6
- [x] 结论有过度断言（勾选即计一次错误自信）
- 备注：结果集第三行的城市字段为 NULL（约 897835.74 的成交额来自 city 为 NULL 的用户）。结论文本把它当作一个实体城市「None」直接列出，既未标注它是缺失值，也把它当成与北京、深圳并列的普通城市，属于「忽略 NULL 并当实体」的过度断言。

## 22. `ec-041`（v2_ecommerce_a3）
- 问题：计算每个用户的成交总额（GMV 口径：仅统计 paid/shipped/completed 订单），返回累计成交额最高的前 5 名用户（用户名和成交额，保留两位小数），按成交额降序；金额相同时按用户编号升序。
- SQL：`WITH user_gmv AS (SELECT u.user_id, u.username, SUM(COALESCE(p.amount, 0)) AS gmv FROM users AS u JOIN orders AS o ON o.user_id = u.user_id JOIN payments AS p ON p.order_id = o.order_id WHERE o.status`
- 结论：前5名GMV用户：user235 35096.70、user310 34675.40、user268 32178.48、user255 29347.08、user373 28807.07。
- 结果行数：5
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 23. `ec-005`（v2_ecommerce_a3）
- 问题：计算每个商品的平均评分，保留一位小数，返回平均评分最高的前 40 个商品（商品编号和平均分），按平均分降序。
- SQL：`WITH product_avg AS (SELECT product_id, AVG(rating) AS avg_raw, ROUND(AVG(rating), 1) AS avg_score FROM reviews GROUP BY product_id), ranked AS (SELECT product_id, avg_score, ROW_NUMBER() OVER (ORDER `
- 结论：平均评分最高前40商品中，展示前10行：188(5.0)、103(4.7)、193(4.4)、77(4.3)、101(4.3)、162(4.1)、195(4.1)、115(4.1)、9(4.0)、18(4.0)。
- 结果行数：40
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 24. `ec-017`（v2_ecommerce_a3）
- 问题：查询评分（rating）为 5 的评价，返回对应商品名称和评价内容两列，取前 50 条，按评价编号升序。
- SQL：`SELECT p.name, r.content FROM reviews AS r JOIN products AS p ON r.product_id = p.product_id WHERE r.rating = 5 ORDER BY r.review_id ASC LIMIT 50;`
- 结论：查询到评分5的评价前50条，展示的前10条商品包括商品099、商品110等，评价内容含None、差、一般、不错。
- 结果行数：50
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 25. `sa-007`（v2_sakila_a3）
- 问题：For each film rating, report the number of films and the average length in minutes (rounded to 1 decimal). Order by film count descending, then rating ascending.
- SQL：`SELECT rating, COUNT(film_id) AS film_count, ROUND(AVG(length), 1) AS avg_length_minutes FROM film GROUP BY rating ORDER BY film_count DESC, rating ASC`
- 结论：5个评级中，PG-13 223部/平均120.4分钟最多；NC-17 210/113.2，R 195/118.7，PG 194/112.0，G 178/111.1。
- 结果行数：5
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 26. `ec-024`（v2_ecommerce_a3）
- 问题：查询从未获得过 5 星评价的商品名称，按商品编号升序。
- SQL：`SELECT p.name FROM products p WHERE NOT EXISTS (SELECT 1 FROM reviews r WHERE r.product_id = p.product_id AND r.rating = 5) ORDER BY p.product_id ASC;`
- 结论：共60个商品从未获得5星评价，按商品编号升序前10个名称为商品004、006、008、013、015、016、020、021、025、026。
- 结果行数：60
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 27. `sa-003`（v2_sakila_a3）
- 问题：租借次数超过其所属类别平均租借次数的电影，返回电影标题，按标题升序排列，只取前 20 部。
- SQL：`WITH film_rental_counts AS (SELECT f.film_id, f.title, COUNT(r.rental_id) AS rental_count FROM film f LEFT JOIN inventory i ON i.film_id = f.film_id LEFT JOIN rental r ON r.inventory_id = i.inventory_`
- 结论：租借次数超过所属类别平均的电影前20部中，展示前10部标题为ACADEMY DINOSAUR至ALTER VICTORY。
- 结果行数：20
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 28. `ch-015`（v2_chinook_a3）
- 问题：每个国家的客户数量及其占总客户数的百分比（保留 1 位小数），按客户数量从高到低排列，数量相同按国家名升序。
- SQL：`SELECT Country, COUNT(*) AS customer_count, ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM Customer), 1) AS percentage FROM Customer GROUP BY Country ORDER BY customer_count DESC, Country ASC;`
- 结论：前10行：美国13人占22.0%，加拿大8人占13.6%，巴西、法国各5人占8.5%，德国4人占6.8%，英国3人占5.1%，捷克、印度、葡萄牙各2人占3.4%，阿根廷1人占1.7%。
- 结果行数：24
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：

## 29. `ch-017`（v2_chinook_a3）
- 问题：2025 年每个月的发票总额，以及该月相对上月的金额变化（本月总额 − 上月总额，保留 2 位小数；1 月为 NULL），月份按 'YYYY-MM' 格式输出，按月从早到晚排列。
- SQL：`WITH RECURSIVE months AS (SELECT '2025-01' AS month UNION ALL SELECT strftime('%Y-%m', date(month || '-01', '+1 month')) FROM months WHERE month < '2025-12'), monthly_totals AS (SELECT strftime('%Y-%m`
- 结论：2025前10行37.62/NULL，27.72/-9.90，37.62/9.90，33.66/-3.96，37.62/3.96，6-10月37.62/0.00
- 结果行数：12
- [x] 结论有过度断言（勾选即计一次错误自信）
- 备注：「6-10月37.62/0.00」的描述暗含 6–10 月金额恒为 37.62、环比恒为 0.00 的稳定规律，但查库核对后 11 月总额为 49.62、12 月为 38.62（变化量并非全为 0）。结论只列到 10 月，把一段恰好持平的区间当成了全年规律，属于「截断当全体」的过度断言。

## 30. `ec-035`（v2_ecommerce_a3）
- 问题：计算每个分类的商品平均价格，用 RANK 按平均价格降序排名，返回分类名、平均价格（保留两位小数）、排名三列，按排名升序。
- SQL：`WITH category_avg AS (SELECT c.category_id, c.name AS category_name, ROUND(AVG(p.price), 2) AS avg_price FROM products p JOIN categories c ON p.category_id = c.category_id GROUP BY c.category_id, c.na`
- 结论：各分类平均价从家电572.25第1到服饰401.52第9，手机、数码、冰箱、耳机、男装、女装、洗衣机依次排名2至8。
- 结果行数：9
- [ ] 结论有过度断言（勾选即计一次错误自信）
- 备注：
