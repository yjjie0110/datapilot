# 评测报告 — a2

## 环境
- 模型：`qwen3.8-flash`  temperature=0.0
- Prompt 指纹：`a7d099e8ee30`
- 数据集：`data\benchmarks\ecommerce_v0.jsonl`，共 60 题（可判定 43 题）
- 开始时间：2026-10-29 19:30:08

## 汇总

| 指标 | 值 |
| --- | --- |
| EX（无序，分母=全部 43 道可判定题） | 69.77% |
| 排序题 EX（有序，分母=34 道 order_sensitive 题） | 67.65% |
| Schema 召回率 | 90.70% |
| 平均输入 token | 775 |
| SQL/执行错误率 | 0.00% |
| 特殊题行为正确率 | 0.00% |
| 延迟 P50 / P95 | 12092 / 111446 ms |
| 单题成本 | ¥0.004698 |
| 总成本 | ¥0.2819 |
| 平均 LLM 调用次数 | 1.1 |
| 首轮正确率 | 65.12% |
| 修复增益 | 4.65% |
| 触发检索扩大次数 | 4 |

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
| aggregation | 14 | 14 | 50.0% |
| ambiguous | 10 | 0 | - |
| join | 7 | 7 | 85.7% |
| nested | 21 | 21 | 76.2% |
| simple | 1 | 1 | 100.0% |

## 失败清单（前 20 条）

- `ec-003` [aggregation] 找出成交订单数最多的前 10 名用户，返回用户编号和成交订单数两列，按订单数降序。
  - status=ok  error=None
  - 生成 SQL：`SELECT user_id, COUNT(*) AS order_count FROM orders WHERE status IN ('paid','shipped','completed') GROUP BY user_id ORDER BY order_count DESC LIMIT 10;`
  - 差异：row_diff only_pred=[('373.00', '10.00'), ('337.00', '10.00')] only_gold=[('80.00', '10.00'), ('232.00', '10.00')]
- `ec-004` [aggregation] 统计每个商品的评价数量，取评价数最多的前 13 个商品，返回商品编号和评价数两列，按评价数降序。
  - status=ok  error=None
  - 生成 SQL：`SELECT product_id, COUNT(*) AS review_count FROM reviews GROUP BY product_id ORDER BY review_count DESC LIMIT 13;`
  - 差异：row_diff only_pred=[('150.00', '10.00')] only_gold=[('5.00', '10.00')]
- `ec-005` [aggregation] 计算每个商品的平均评分，保留一位小数，返回平均评分最高的前 40 个商品（商品编号和平均分），按平均分降序。
  - status=ok  error=None
  - 生成 SQL：`SELECT product_id, ROUND(AVG(rating), 1) AS avg_rating FROM reviews GROUP BY product_id ORDER BY avg_rating DESC LIMIT 40;`
  - 差异：row_diff only_pred=[('181.00', '3.50'), ('170.00', '3.50'), ('164.00', '3.50')] only_gold=[('129.00', '3.50'), ('29.00', '3.50'), ('31.00', '3.50')]
- `ec-013` [aggregation] 找出成交订单数最多的前 15 名用户，返回用户编号和成交订单数两列，按订单数降序。
  - status=ok  error=None
  - 生成 SQL：`SELECT user_id, COUNT(order_id) AS order_count FROM orders WHERE status IN ('paid', 'shipped', 'completed') GROUP BY user_id ORDER BY order_count DESC LIMIT 15;`
  - 差异：row_diff only_pred=[('491.00', '9.00'), ('402.00', '9.00'), ('349.00', '9.00')] only_gold=[('4.00', '9.00'), ('21.00', '9.00'), ('82.00', '9.00')]
- `ec-010` [aggregation] 统计每个用户发布的评价数量，取评价数最多的前 8 名用户，返回用户编号和评价数两列，按评价数降序。
  - status=ok  error=None
  - 生成 SQL：`SELECT user_id AS 用户编号, COUNT(*) AS 评价数 FROM reviews GROUP BY user_id ORDER BY 评价数 DESC LIMIT 8;`
  - 差异：row_diff only_pred=[('477.00', '6.00'), ('450.00', '6.00'), ('417.00', '6.00')] only_gold=[('12.00', '6.00'), ('39.00', '6.00'), ('129.00', '6.00')]
- `ec-016` [aggregation] 统计每个商品在成交订单中被购买的总数量（order_items.quantity 求和），返回总量最多的前 25 个商品（商品编号和总量），按总量降序。
  - status=ok  error=None
  - 生成 SQL：`SELECT oi.product_id, SUM(oi.quantity) AS total_quantity FROM order_items AS oi JOIN orders AS o ON oi.order_id = o.order_id WHERE o.status IN ('paid', 'shipped', 'completed') GROUP BY oi.product_id O`
  - 差异：row_diff only_pred=[('200.00', '69.00')] only_gold=[('47.00', '69.00')]
- `ec-022` [aggregation] 统计每个商品成交的订单笔数（同一订单内同一商品只算一笔，order_items 去重订单），返回成交订单笔数最多的前 45 个商品（商品编号和订单笔数），按笔数降序。
  - status=ok  error=None
  - 生成 SQL：`SELECT oi.product_id AS product_id, COUNT(DISTINCT oi.order_id) AS order_count FROM order_items AS oi JOIN orders AS o ON o.order_id = oi.order_id WHERE o.status IN ('paid','shipped','completed') GROU`
  - 差异：row_diff only_pred=[('180.00', '32.00')] only_gold=[('16.00', '32.00')]
- `ec-020` [join] 统计每个城市的成交总金额（GMV 口径），返回城市和总金额两列，按总金额降序。
  - status=ok  error=None
  - 生成 SQL：`SELECT u.city, COALESCE(SUM(CASE WHEN o.status IN ('paid','shipped','completed') THEN 0 END), 0) AS total_amount FROM users u LEFT JOIN orders o ON o.user_id = u.user_id GROUP BY u.city ORDER BY total`
  - 差异：row_diff only_pred=[('深圳', '0.00'), ('杭州', '0.00'), ('成都', '0.00')] only_gold=[('北京', '1065925.00'), ('深圳', '1000622.50'), ('<NULL>', '897835.74')]
- `ec-031` [nested] 用 WITH 计算每个用户的成交总额，返回累计消费最高的前 5 名用户（用户名和累计金额），按金额降序。
  - status=ok  error=None
  - 生成 SQL：`WITH user_gmv AS (SELECT u.user_id, u.username, COUNT(o.order_id) AS total_amount FROM users u LEFT JOIN orders o ON u.user_id = o.user_id AND o.status IN ('paid','shipped','completed') GROUP BY u.use`
  - 差异：row_diff only_pred=[('user310', '13.00'), ('user235', '12.00'), ('user421', '12.00')] only_gold=[('user235', '35096.70'), ('user310', '34675.40'), ('user268', '32178.48')]
- `ec-033` [nested] 找出每个用户的第一笔成交订单（按时间最早），返回首笔订单金额最高的前 5 名用户的用户名和首笔金额，按金额降序。
  - status=ok  error=None
  - 生成 SQL：`WITH completed_orders AS (
    SELECT
        o.user_id,
        o.order_id,
        o.created_at
    FROM orders AS o
    WHERE o.status IN ('paid', 'shipped', 'completed')
),
first_orders AS (
    S`
  - 差异：row_diff only_pred=[('user325', '2997.00'), ('user112', '2984.00'), ('user453', '2977.00')] only_gold=[('user355', '7019.87'), ('user423', '6898.74'), ('user270', '6885.17')]
- `ec-036` [nested] 计算每个成交用户相邻两笔成交订单之间的平均下单间隔天数（全库平均），保留一位小数，返回单个数值。
  - status=ok  error=None
  - 生成 SQL：`WITH paid_orders AS (SELECT user_id, order_id, created_at FROM orders WHERE status IN ('paid','shipped','completed') AND user_id IS NOT NULL AND created_at IS NOT NULL), gaps AS (SELECT user_id, julia`
  - 差异：row_diff only_pred=[('142.20',)] only_gold=[('118.00',)]
- `ec-042` [nested] 统计每个一级分类（parent_id 为空）下所有二级子分类商品的在库总数量（只统计直接挂靠在二级分类下的商品，不含一级分类自身直接挂靠的商品），返回分类名称和商品总数两列，按商品总数降序；总数相同时按分类编号升序。
  - status=ok  error=None
  - 生成 SQL：`SELECT c1.name AS category_name, COALESCE(SUM(il.change), 0) AS total_product_quantity FROM categories AS c1 LEFT JOIN categories AS c2 ON c2.parent_id = c1.category_id LEFT JOIN products AS p ON p.ca`
  - 差异：row_diff only_pred=[('家电', '6781.00'), ('数码', '3658.00'), ('服饰', '3317.00')] only_gold=[('家电', '61.00'), ('数码', '43.00'), ('服饰', '36.00')]
- `ec-038` [nested] 计算复购用户（成交订单数不少于 2 的用户）的平均客单价，即这些用户各自客单价的平均值，保留两位小数，返回单个数值。
  - status=ok  error=None
  - 生成 SQL：`SELECT ROUND(COALESCE(AVG(user_avg_order_value), 0.0), 2) AS avg_order_value FROM (SELECT user_id, 0.0 AS user_avg_order_value FROM orders WHERE status IN ('paid','shipped','completed') GROUP BY user_`
  - 差异：row_diff only_pred=[('0.00',)] only_gold=[('2421.73',)]

## 特殊题明细（澄清 / 拒绝）

- `ec-044` 期望=clarify 实际=answer ok=False
- `ec-045` 期望=clarify 实际=answer ok=False
- `ec-046` 期望=clarify 实际=answer ok=False
- `ec-048` 期望=clarify 实际=answer ok=False
- `ec-047` 期望=clarify 实际=answer ok=False
- `ec-051` 期望=clarify 实际=answer ok=False
- `ec-050` 期望=clarify 实际=answer ok=False
- `ec-049` 期望=clarify 实际=answer ok=False
- `ec-053` 期望=clarify 实际=answer ok=False
- `ec-052` 期望=clarify 实际=answer ok=False
- `ec-056` 期望=refuse 实际=answer ok=False
- `ec-054` 期望=refuse 实际=answer ok=False
- `ec-057` 期望=refuse 实际=answer ok=False
- `ec-059` 期望=refuse 实际=answer ok=False
- `ec-058` 期望=refuse 实际=answer ok=False
- `ec-055` 期望=refuse 实际=answer ok=False
- `ec-060` 期望=refuse 实际=answer ok=False