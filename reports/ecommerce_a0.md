# 评测报告 — a0

## 环境
- 模型：`qwen3.8-flash`  temperature=0.0
- Prompt 指纹：`084699c0f060`
- 数据集：`data\benchmarks\ecommerce_v0.jsonl`，共 60 题（可判定 43 题）
- 开始时间：2026-10-28 19:45:52

## 汇总

| 指标 | 值 |
| --- | --- |
| EX（无序，分母=全部 43 道可判定题） | 72.09% |
| 排序题 EX（有序，分母=37 道 order_sensitive 题） | 75.68% |
| Schema 召回率 | N/A |
| 平均输入 token | N/A |
| SQL/执行错误率 | 0.00% |
| 特殊题行为正确率 | 0.00% |
| 延迟 P50 / P95 | 10205 / 37692 ms |
| 单题成本 | ¥0.002369 |
| 总成本 | ¥0.1421 |
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
| aggregation | 12 | 12 | 50.0% |
| ambiguous | 10 | 0 | - |
| join | 12 | 12 | 75.0% |
| nested | 9 | 9 | 77.8% |
| simple | 10 | 10 | 90.0% |

## 失败清单（前 20 条）

- `ec-006` [simple] 查询价格在 200 到 600 元之间（含边界）且在售的商品名称和价格，按商品编号升序。
  - status=ok  error=None
  - 生成 SQL：`SELECT name, price FROM products WHERE price BETWEEN 200 AND 600 AND status = '在售' ORDER BY product_id ASC`
  - 差异：row_count_diff pred=0 gold=72
- `ec-011` [aggregation] 统计每个城市的用户数量，按数量从高到低排列；数量相同时按城市名升序。
  - status=ok  error=None
  - 生成 SQL：`SELECT city, COUNT(user_id) AS user_count FROM users WHERE city IS NOT NULL GROUP BY city ORDER BY user_count DESC, city ASC`
  - 差异：row_count_diff pred=5 gold=6
- `ec-014` [aggregation] 计算所有在售商品的平均价格，保留两位小数，返回单个数值。
  - status=ok  error=None
  - 生成 SQL：`SELECT ROUND(AVG(price), 2) AS avg_price FROM products WHERE status = '在售';`
  - 差异：row_diff only_pred=[('<NULL>',)] only_gold=[('492.16',)]
- `ec-016` [aggregation] 统计每个商品的评价数量，取评价数最多的前 5 个商品，返回商品编号和评价数，按评价数降序。
  - status=ok  error=None
  - 生成 SQL：`SELECT product_id, COUNT(*) AS review_count FROM reviews GROUP BY product_id ORDER BY review_count DESC LIMIT 5`
  - 差异：row_diff only_pred=[('192.00', '11.00')] only_gold=[('66.00', '11.00')]
- `ec-017` [aggregation] 计算每个商品的平均评分，保留一位小数，返回平均评分最高的前 10 个商品（商品编号和平均分），按平均分降序。
  - status=ok  error=None
  - 生成 SQL：`SELECT product_id, ROUND(AVG(rating), 1) AS avg_rating FROM reviews GROUP BY product_id ORDER BY avg_rating DESC LIMIT 10;`
  - 差异：row_diff only_pred=[('178.00', '4.00'), ('121.00', '4.00')] only_gold=[('9.00', '4.00'), ('18.00', '4.00')]
- `ec-013` [aggregation] 统计每个一级分类（parent_id 为空的分类）下在售商品的数量，按数量降序；用分类名输出。
  - status=ok  error=None
  - 生成 SQL：`SELECT c.name AS category_name, COUNT(p.product_id) AS on_sale_count FROM categories c LEFT JOIN products p ON p.category_id = c.category_id AND LOWER(p.status) = 'on_sale' WHERE c.parent_id IS NULL G`
  - 差异：row_diff only_pred=[('数码', '0.00'), ('家电', '0.00'), ('服饰', '0.00')] only_gold=[('服饰', '21.00'), ('家电', '18.00'), ('数码', '14.00')]
- `ec-015` [aggregation] 找出成交订单数最多的前 10 名用户，返回用户编号和成交订单数两列，按订单数降序。
  - status=ok  error=None
  - 生成 SQL：`WITH paid_orders AS (SELECT DISTINCT o.user_id, o.order_id FROM orders AS o JOIN payments AS p ON p.order_id = o.order_id) SELECT user_id, COUNT(order_id) AS completed_order_count FROM paid_orders GRO`
  - 差异：row_diff only_pred=[('373.00', '10.00'), ('337.00', '10.00')] only_gold=[('80.00', '10.00'), ('232.00', '10.00')]
- `ec-023` [join] 列出成交订单中下单金额（payments.amount）最高的前 50 笔，返回订单编号、用户名、支付金额三列，按金额降序。
  - status=ok  error=None
  - 生成 SQL：`SELECT o.order_id AS order_id, u.username AS username, SUM(p.amount) AS payment_amount FROM orders o JOIN users u ON u.user_id = o.user_id JOIN payments p ON p.order_id = o.order_id WHERE o.status = '`
  - 差异：row_diff only_pred=[('524.00', 'user313', '6200.13'), ('2407.00', 'user165', '6195.49'), ('239.00', 'user219', '6179.27')] only_gold=[('1875.00', 'user286', '7697.14'), ('815.00', 'user066', '7266.99'), ('2516.00', 'user268', '7163.29')]
- `ec-030` [join] 列出使用过优惠券的订单中支付金额最高的前 50 个，返回订单编号、优惠券编码、折扣率三列，按订单编号升序。
  - status=ok  error=None
  - 生成 SQL：`WITH paid AS (SELECT o.order_id, o.coupon_id, SUM(p.amount) AS total_paid FROM orders o JOIN payments p ON p.order_id = o.order_id WHERE o.coupon_id IS NOT NULL GROUP BY o.order_id, o.coupon_id), top5`
  - 差异：row_diff only_pred=[('288.00', 'CP012', '10.00'), ('425.00', 'CP026', '10.00'), ('481.00', 'CP019', '15.00')] only_gold=[('19.00', 'CP020', '15.00'), ('22.00', 'CP018', '20.00'), ('27.00', 'CP009', '15.00')]
- `ec-032` [join] 统计每个城市的成交总金额（GMV 口径），返回城市和总金额两列，按总金额降序。
  - status=ok  error=None
  - 生成 SQL：`WITH order_gmv AS (SELECT order_id, SUM(quantity * unit_price) AS gmv FROM order_items GROUP BY order_id) SELECT u.city, SUM(og.gmv) AS total_gmv FROM orders o JOIN users u ON o.user_id = u.user_id JO`
  - 差异：row_diff only_pred=[('北京', '1095050.41'), ('深圳', '1021541.76'), ('<NULL>', '918169.28')] only_gold=[('北京', '1065925.00'), ('深圳', '1000622.50'), ('<NULL>', '897835.74')]
- `ec-040` [nested] 用 WITH 统计每个城市的成交订单数，返回成交订单数最多的城市及其订单数两列。
  - status=ok  error=None
  - 生成 SQL：`WITH city_orders AS (SELECT u.city AS city, COUNT(*) AS order_count FROM orders AS o JOIN users AS u ON o.user_id = u.user_id WHERE o.status = 'completed' AND u.city IS NOT NULL GROUP BY u.city) SELEC`
  - 差异：row_diff only_pred=[('北京', '321.00')] only_gold=[('北京', '436.00')]
- `ec-039` [nested] 用 WITH 找出成交订单数最多的一名用户，返回用户编号和成交订单数两列。
  - status=ok  error=None
  - 生成 SQL：`WITH order_counts AS (SELECT user_id, COUNT(*) AS order_count FROM orders WHERE user_id IS NOT NULL AND status = 'completed' GROUP BY user_id) SELECT user_id, order_count FROM order_counts ORDER BY or`
  - 差异：row_diff only_pred=[('235.00', '11.00')] only_gold=[('310.00', '13.00')]

## 特殊题明细（澄清 / 拒绝）

- `ec-044` 期望=clarify 实际=answer ok=False
- `ec-045` 期望=clarify 实际=answer ok=False
- `ec-048` 期望=clarify 实际=answer ok=False
- `ec-046` 期望=clarify 实际=answer ok=False
- `ec-049` 期望=clarify 实际=answer ok=False
- `ec-050` 期望=clarify 实际=answer ok=False
- `ec-051` 期望=clarify 实际=answer ok=False
- `ec-052` 期望=clarify 实际=answer ok=False
- `ec-053` 期望=clarify 实际=answer ok=False
- `ec-047` 期望=clarify 实际=answer ok=False
- `ec-056` 期望=refuse 实际=answer ok=False
- `ec-054` 期望=refuse 实际=answer ok=False
- `ec-057` 期望=refuse 实际=answer ok=False
- `ec-059` 期望=refuse 实际=answer ok=False
- `ec-055` 期望=refuse 实际=answer ok=False
- `ec-060` 期望=refuse 实际=answer ok=False
- `ec-058` 期望=refuse 实际=answer ok=False