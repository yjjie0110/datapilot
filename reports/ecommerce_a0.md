# 评测报告 — a0

## 环境
- 模型：`qwen3.8-flash`  temperature=0.0
- Prompt 指纹：`084699c0f060`
- 数据集：`data\benchmarks\ecommerce_v0.jsonl`，共 60 题（可判定 43 题）
- 开始时间：2026-10-28 19:01:11

## 汇总

| 指标 | 值 |
| --- | --- |
| EX（无序，分母=全部 43 道可判定题） | 60.47% |
| 排序题 EX（有序，分母=9 道 order_sensitive 题） | 22.22% |
| Schema 召回率 | N/A |
| 平均输入 token | N/A |
| SQL/执行错误率 | 0.00% |
| 特殊题行为正确率 | 0.00% |
| 延迟 P50 / P95 | 8398 / 43463 ms |
| 单题成本 | ¥0.002381 |
| 总成本 | ¥0.1428 |
| 平均 LLM 调用次数 | 1.0 |
| 首轮正确率 | N/A |
| 修复增益 | N/A |
| 触发检索扩大次数 | 0 |

## 行为混淆矩阵
| 期望 \ 实际 | answer |
| --- | --- |
| answer | 43 |
| clarify | 10 |
| refuse | 7 |
## 分题型

| 题型 | 题目数 | 可判定题 | EX |
| --- | --- | --- | --- |
| adversarial | 7 | 0 | - |
| aggregation | 12 | 12 | 25.0% |
| ambiguous | 10 | 0 | - |
| join | 12 | 12 | 75.0% |
| nested | 9 | 9 | 55.6% |
| simple | 10 | 10 | 90.0% |

## 失败清单（前 20 条）

- `ec-006` [simple] 查询价格在 100 到 500 之间（含边界）且在售的商品名称和价格。
  - status=ok  error=None
  - 生成 SQL：`SELECT name, price FROM products WHERE price BETWEEN 100 AND 500 AND status = '在售';`
  - 差异：row_count_diff pred=0 gold=77
- `ec-014` [aggregation] 计算所有在售商品的平均价格，保留两位小数。
  - status=ok  error=None
  - 生成 SQL：`SELECT ROUND(AVG(price), 2) AS avg_price FROM products WHERE status = 'on_sale'`
  - 差异：row_diff only_pred=[('<NULL>',)] only_gold=[('492.16',)]
- `ec-011` [aggregation] 统计每个城市的用户数量，按数量从高到低排列。
  - status=ok  error=None
  - 生成 SQL：`SELECT city, COUNT(*) AS user_count FROM users WHERE city IS NOT NULL GROUP BY city ORDER BY user_count DESC;`
  - 差异：row_count_diff pred=5 gold=6
- `ec-013` [aggregation] 统计每个一级分类（parent_id 为空的分类）下有多少商品。
  - status=ok  error=None
  - 生成 SQL：`SELECT c.category_id, c.name, COUNT(p.product_id) AS product_count FROM categories AS c LEFT JOIN products AS p ON c.category_id = p.category_id WHERE c.parent_id IS NULL GROUP BY c.category_id, c.nam`
  - 差异：col_count_diff pred=3 gold=2
- `ec-016` [aggregation] 统计每个商品的评价数量（rating 条数），取评价数最多的前 5 个商品。
  - status=ok  error=None
  - 生成 SQL：`SELECT p.product_id, p.name, COUNT(r.rating) AS review_count FROM products AS p LEFT JOIN reviews AS r ON p.product_id = r.product_id GROUP BY p.product_id, p.name ORDER BY review_count DESC, p.produc`
  - 差异：col_count_diff pred=3 gold=2
- `ec-018` [aggregation] 统计每个供应商供应的商品数量，按数量从高到低。
  - status=ok  error=None
  - 生成 SQL：`SELECT s.supplier_id, s.name, COUNT(p.product_id) AS product_count FROM suppliers s LEFT JOIN products p ON s.supplier_id = p.supplier_id GROUP BY s.supplier_id, s.name ORDER BY product_count DESC;`
  - 差异：col_count_diff pred=3 gold=2
- `ec-015` [aggregation] 找出成交订单数最多的前 10 名用户，返回用户编号和成交订单数，按订单数降序。
  - status=ok  error=None
  - 生成 SQL：`SELECT o.user_id, COUNT(DISTINCT o.order_id) AS order_count FROM orders AS o JOIN payments AS p ON o.order_id = p.order_id GROUP BY o.user_id ORDER BY order_count DESC LIMIT 10;`
  - 差异：row_diff only_pred=[('373.00', '10.00'), ('337.00', '10.00')] only_gold=[('80.00', '10.00'), ('232.00', '10.00')]
- `ec-017` [aggregation] 计算每个商品的平均评分，保留一位小数，按平均评分从高到低。
  - status=ok  error=None
  - 生成 SQL：`SELECT p.product_id, p.name, ROUND(AVG(r.rating), 1) AS avg_rating FROM products AS p LEFT JOIN reviews AS r ON p.product_id = r.product_id GROUP BY p.product_id, p.name ORDER BY avg_rating DESC;`
  - 差异：row_count_diff pred=200 gold=10
- `ec-020` [aggregation] 统计每个商品被购买的总数量（所有订单明细 quantity 求和），取总量前 3 的商品。
  - status=ok  error=None
  - 生成 SQL：`SELECT p.product_id, p.name, SUM(oi.quantity) AS total_quantity FROM order_items AS oi JOIN products AS p ON p.product_id = oi.product_id GROUP BY p.product_id, p.name ORDER BY total_quantity DESC LIM`
  - 差异：col_count_diff pred=3 gold=2
- `ec-022` [aggregation] 计算每个商品的总库存变动（inventory_logs 的 change 求和），按变动量从高到低取前 5 个商品。
  - status=ok  error=None
  - 生成 SQL：`SELECT il.product_id, p.name, SUM(il.change) AS total_change FROM inventory_logs il JOIN products p ON il.product_id = p.product_id GROUP BY il.product_id, p.name ORDER BY total_change DESC LIMIT 5;`
  - 差异：col_count_diff pred=3 gold=2
- `ec-028` [join] 列出前 50 笔有物流记录的订单编号、承运商（carrier）和发货时间。
  - status=ok  error=None
  - 生成 SQL：`SELECT order_id, carrier, shipped_at FROM shipments ORDER BY shipped_at ASC LIMIT 50;`
  - 差异：row_diff only_pred=[('1954.00', '中通', '2024-01-01'), ('717.00', '圆通', '2024-01-02'), ('1629.00', '中通', '2024-01-02')] only_gold=[('1.00', '中通', '2025-06-03'), ('3.00', '圆通', '2024-04-18'), ('4.00', '中通', '2024-04-17')]
- `ec-023` [join] 列出前 50 笔成交订单的订单编号、下单用户名和订单状态。
  - status=ok  error=None
  - 生成 SQL：`SELECT o.order_id, u.username, o.status FROM orders AS o JOIN users AS u ON o.user_id = u.user_id WHERE o.status = 'completed' ORDER BY o.created_at, o.order_id LIMIT 50;`
  - 差异：row_diff only_pred=[('717.00', 'user245', 'completed'), ('1629.00', 'user133', 'completed'), ('2399.00', 'user486', 'completed')] only_gold=[('1.00', 'user444', 'completed'), ('3.00', 'user478', 'completed'), ('4.00', 'user373', 'completed')]
- `ec-032` [join] 列出前 50 笔成交订单的订单编号、用户名、城市和支付金额。
  - status=ok  error=None
  - 生成 SQL：`SELECT o.order_id, u.username, u.city, SUM(p.amount) AS payment_amount FROM orders AS o JOIN users AS u ON u.user_id = o.user_id LEFT JOIN payments AS p ON p.order_id = o.order_id WHERE LOWER(o.status`
  - 差异：row_diff only_pred=[('717.00', 'user245', '北京', '2835.78'), ('1629.00', 'user133', '深圳', '1271.97'), ('2399.00', 'user486', '北京', '2123.30')] only_gold=[('1.00', 'user444', '深圳', '15.04'), ('3.00', 'user478', '北京', '346.78'), ('4.00', 'user373', '深圳', '2519.65')]
- `ec-038` [nested] 查询用户名以 'user0' 开头且下过订单的用户（去重），取前 50 个。
  - status=ok  error=None
  - 生成 SQL：`SELECT u.* FROM users AS u WHERE u.username LIKE 'user0%' AND EXISTS (SELECT 1 FROM orders AS o WHERE o.user_id = u.user_id) ORDER BY u.user_id LIMIT 50;`
  - 差异：col_count_diff pred=6 gold=1
- `ec-040` [nested] 用 WITH 统计每个城市的成交订单数，返回成交订单数最多的城市及其订单数。
  - status=ok  error=None
  - 生成 SQL：`WITH city_orders AS (SELECT u.city AS city, COUNT(o.order_id) AS order_count FROM orders AS o JOIN users AS u ON o.user_id = u.user_id WHERE LOWER(o.status) = 'completed' AND u.city IS NOT NULL GROUP `
  - 差异：row_diff only_pred=[('北京', '321.00')] only_gold=[('北京', '436.00')]
- `ec-039` [nested] 用 WITH 找出成交订单数最多的一名用户，返回其用户编号和订单数。
  - status=ok  error=None
  - 生成 SQL：`WITH user_order_counts AS (SELECT user_id, COUNT(*) AS order_count FROM orders WHERE status = 'completed' GROUP BY user_id) SELECT user_id, order_count FROM user_order_counts ORDER BY order_count DESC`
  - 差异：row_diff only_pred=[('235.00', '11.00')] only_gold=[('310.00', '13.00')]
- `ec-041` [nested] 查询每个分类中价格最高的商品名称和价格。
  - status=ok  error=None
  - 生成 SQL：`WITH ranked_products AS (SELECT c.category_id, c.name AS category_name, p.name AS product_name, p.price AS product_price, ROW_NUMBER() OVER (PARTITION BY p.category_id ORDER BY p.price DESC, p.product`
  - 差异：col_count_diff pred=4 gold=2

## 特殊题明细（澄清 / 拒绝）

- `ec-044` 期望=clarify 实际=answer ok=False
- `ec-045` 期望=clarify 实际=answer ok=False
- `ec-046` 期望=clarify 实际=answer ok=False
- `ec-048` 期望=clarify 实际=answer ok=False
- `ec-050` 期望=clarify 实际=answer ok=False
- `ec-049` 期望=clarify 实际=answer ok=False
- `ec-051` 期望=clarify 实际=answer ok=False
- `ec-052` 期望=clarify 实际=answer ok=False
- `ec-053` 期望=clarify 实际=answer ok=False
- `ec-056` 期望=refuse 实际=answer ok=False
- `ec-054` 期望=refuse 实际=answer ok=False
- `ec-057` 期望=refuse 实际=answer ok=False
- `ec-059` 期望=refuse 实际=answer ok=False
- `ec-060` 期望=refuse 实际=answer ok=False
- `ec-055` 期望=refuse 实际=answer ok=False
- `ec-047` 期望=clarify 实际=answer ok=False
- `ec-058` 期望=refuse 实际=answer ok=False