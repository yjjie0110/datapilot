# 评测报告 — a1

## 环境
- 模型：`qwen3.8-flash`  temperature=0.0
- Prompt 指纹：`a7d099e8ee30`
- 数据集：`data\benchmarks\ecommerce_v0.jsonl`，共 60 题（可判定 43 题）
- 开始时间：2026-10-29 19:19:06

## 汇总

| 指标 | 值 |
| --- | --- |
| EX（无序，分母=全部 43 道可判定题） | 67.44% |
| 排序题 EX（有序，分母=34 道 order_sensitive 题） | 61.76% |
| Schema 召回率 | 83.72% |
| 平均输入 token | 717 |
| SQL/执行错误率 | 2.33% |
| 特殊题行为正确率 | 0.00% |
| 延迟 P50 / P95 | 15912 / 54386 ms |
| 单题成本 | ¥0.004197 |
| 总成本 | ¥0.2518 |
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
| aggregation | 14 | 14 | 35.7% |
| ambiguous | 10 | 0 | - |
| join | 7 | 7 | 71.4% |
| nested | 21 | 21 | 85.7% |
| simple | 1 | 1 | 100.0% |

## 失败清单（前 20 条）

- `ec-003` [aggregation] 找出成交订单数最多的前 10 名用户，返回用户编号和成交订单数两列，按订单数降序。
  - status=ok  error=None
  - 生成 SQL：`SELECT user_id, COUNT(*) AS order_count FROM orders WHERE status IN ('paid','shipped','completed') GROUP BY user_id ORDER BY order_count DESC LIMIT 10;`
  - 差异：row_diff only_pred=[('373.00', '10.00'), ('337.00', '10.00')] only_gold=[('80.00', '10.00'), ('232.00', '10.00')]
- `ec-004` [aggregation] 统计每个商品的评价数量，取评价数最多的前 13 个商品，返回商品编号和评价数两列，按评价数降序。
  - status=ok  error=None
  - 生成 SQL：`SELECT product_id, COUNT(review_id) AS review_count FROM reviews GROUP BY product_id ORDER BY review_count DESC LIMIT 13;`
  - 差异：row_diff only_pred=[('150.00', '10.00')] only_gold=[('5.00', '10.00')]
- `ec-005` [aggregation] 计算每个商品的平均评分，保留一位小数，返回平均评分最高的前 40 个商品（商品编号和平均分），按平均分降序。
  - status=ok  error=None
  - 生成 SQL：`SELECT product_id, ROUND(AVG(rating), 1) AS avg_rating FROM reviews GROUP BY product_id ORDER BY avg_rating DESC, product_id ASC LIMIT 40;`
  - 差异：row_diff only_pred=[('58.00', '3.50')] only_gold=[('129.00', '3.50')]
- `ec-002` [aggregation] 统计每个一级分类（parent_id 为空的分类）下在售商品的数量，按数量降序；用分类名输出。
  - status=ok  error=None
  - 生成 SQL：`WITH RECURSIVE category_tree(root_category_id, category_id, root_name) AS (SELECT category_id, category_id, name FROM categories WHERE parent_id IS NULL UNION ALL SELECT ct.root_category_id, c.categor`
  - 差异：row_diff only_pred=[('家电', '73.00'), ('数码', '54.00'), ('服饰', '53.00')] only_gold=[('服饰', '21.00'), ('家电', '18.00'), ('数码', '14.00')]
- `ec-013` [aggregation] 找出成交订单数最多的前 15 名用户，返回用户编号和成交订单数两列，按订单数降序。
  - status=ok  error=None
  - 生成 SQL：`SELECT user_id, COUNT(*) AS order_count FROM orders WHERE status IN ('paid','shipped','completed') AND user_id IS NOT NULL GROUP BY user_id ORDER BY order_count DESC LIMIT 15;`
  - 差异：row_diff only_pred=[('491.00', '9.00'), ('402.00', '9.00'), ('349.00', '9.00')] only_gold=[('4.00', '9.00'), ('21.00', '9.00'), ('82.00', '9.00')]
- `ec-008` [aggregation] 计算每个城市的成交额占全库总 GMV 的百分比，返回城市和占比（百分比数值，保留两位小数）两列，按占比降序。
  - status=ok  error=None
  - 生成 SQL：`WITH city_gmv AS (SELECT u.city AS city, COUNT(o.order_id) AS gmv FROM orders o JOIN users u ON u.user_id = o.user_id WHERE o.status IN ('paid','shipped','completed') GROUP BY u.city), total_gmv AS (S`
  - 差异：row_diff only_pred=[('北京', '19.13'), ('深圳', '18.60'), ('杭州', '15.93')] only_gold=[('北京', '19.22'), ('深圳', '18.04'), ('<NULL>', '16.19')]
- `ec-010` [aggregation] 统计每个用户发布的评价数量，取评价数最多的前 8 名用户，返回用户编号和评价数两列，按评价数降序。
  - status=ok  error=None
  - 生成 SQL：`SELECT NULL AS user_id, 0 AS review_count FROM (SELECT 1 AS x) AS dummy WHERE 1 = 0 ORDER BY review_count DESC LIMIT 8`
  - 差异：row_count_diff pred=0 gold=8
- `ec-016` [aggregation] 统计每个商品在成交订单中被购买的总数量（order_items.quantity 求和），返回总量最多的前 25 个商品（商品编号和总量），按总量降序。
  - status=ok  error=None
  - 生成 SQL：`SELECT oi.product_id, SUM(oi.quantity) AS total_quantity FROM order_items AS oi JOIN orders AS o ON oi.order_id = o.order_id WHERE o.status IN ('paid', 'shipped', 'completed') GROUP BY oi.product_id O`
  - 差异：row_diff only_pred=[('200.00', '69.00')] only_gold=[('47.00', '69.00')]
- `ec-022` [aggregation] 统计每个商品成交的订单笔数（同一订单内同一商品只算一笔，order_items 去重订单），返回成交订单笔数最多的前 45 个商品（商品编号和订单笔数），按笔数降序。
  - status=ok  error=None
  - 生成 SQL：`SELECT oi.product_id, COUNT(DISTINCT oi.order_id) AS order_count FROM order_items oi JOIN orders o ON o.order_id = oi.order_id WHERE o.status IN ('paid','shipped','completed') GROUP BY oi.product_id O`
  - 差异：row_diff only_pred=[('180.00', '32.00')] only_gold=[('16.00', '32.00')]
- `ec-020` [join] 统计每个城市的成交总金额（GMV 口径），返回城市和总金额两列，按总金额降序。
  - status=ok  error=None
  - 生成 SQL：`SELECT u.city AS city, COUNT(o.order_id) AS total_gmv FROM users AS u JOIN orders AS o ON o.user_id = u.user_id WHERE o.status IN ('paid', 'shipped', 'completed') GROUP BY u.city ORDER BY total_gmv DE`
  - 差异：row_diff only_pred=[('北京', '436.00'), ('深圳', '424.00'), ('杭州', '363.00')] only_gold=[('北京', '1065925.00'), ('深圳', '1000622.50'), ('<NULL>', '897835.74')]
- `ec-018` [join] 列出使用过优惠券的订单中支付金额最高的前 50 个，返回订单编号、优惠券编码、折扣率三列，按支付金额降序；金额相同时按订单编号升序。
  - status=sql_error  error=no such column: c.coupon_code
  - 生成 SQL：`WITH order_payments AS (SELECT o.order_id, o.coupon_id, SUM(p.amount) AS payment_amount FROM orders AS o JOIN payments AS p ON p.order_id = o.order_id WHERE o.status IN ('paid', 'shipped', 'completed'`
- `ec-036` [nested] 计算每个成交用户相邻两笔成交订单之间的平均下单间隔天数（全库平均），保留一位小数，返回单个数值。
  - status=ok  error=None
  - 生成 SQL：`WITH txn_orders AS (SELECT user_id, created_at, LAG(created_at) OVER (PARTITION BY user_id ORDER BY created_at, order_id) AS prev_created_at FROM orders WHERE status IN ('paid', 'shipped', 'completed'`
  - 差异：row_diff only_pred=[('142.20',)] only_gold=[('118.00',)]
- `ec-033` [nested] 找出每个用户的第一笔成交订单（按时间最早），返回首笔订单金额最高的前 5 名用户的用户名和首笔金额，按金额降序。
  - status=ok  error=None
  - 生成 SQL：`WITH transactional_orders AS (SELECT user_id, order_id, created_at FROM orders WHERE status IN ('paid', 'shipped', 'completed')), first_order_per_user AS (SELECT user_id, order_id, created_at, ROW_NUM`
  - 差异：row_diff only_pred=[('user001', '<NULL>'), ('user002', '<NULL>'), ('user003', '<NULL>')] only_gold=[('user355', '7019.87'), ('user423', '6898.74'), ('user270', '6885.17')]
- `ec-042` [nested] 统计每个一级分类（parent_id 为空）下所有二级子分类商品的在库总数量（只统计直接挂靠在二级分类下的商品，不含一级分类自身直接挂靠的商品），返回分类名称和商品总数两列，按商品总数降序；总数相同时按分类编号升序。
  - status=ok  error=None
  - 生成 SQL：`WITH product_inventory AS (SELECT product_id, SUM(change) AS stock_qty FROM inventory_logs GROUP BY product_id) SELECT c1.name AS "分类名称", COALESCE(SUM(pi.stock_qty), 0) AS "商品总数" FROM categories AS c1`
  - 差异：row_diff only_pred=[('家电', '6781.00'), ('数码', '3658.00'), ('服饰', '3317.00')] only_gold=[('家电', '61.00'), ('数码', '43.00'), ('服饰', '36.00')]

## 特殊题明细（澄清 / 拒绝）

- `ec-044` 期望=clarify 实际=answer ok=False
- `ec-047` 期望=clarify 实际=answer ok=False
- `ec-046` 期望=clarify 实际=answer ok=False
- `ec-048` 期望=clarify 实际=answer ok=False
- `ec-049` 期望=clarify 实际=answer ok=False
- `ec-045` 期望=clarify 实际=answer ok=False
- `ec-051` 期望=clarify 实际=answer ok=False
- `ec-052` 期望=clarify 实际=answer ok=False
- `ec-050` 期望=clarify 实际=answer ok=False
- `ec-053` 期望=clarify 实际=answer ok=False
- `ec-054` 期望=refuse 实际=answer ok=False
- `ec-056` 期望=refuse 实际=answer ok=False
- `ec-057` 期望=refuse 实际=answer ok=False
- `ec-055` 期望=refuse 实际=answer ok=False
- `ec-059` 期望=refuse 实际=answer ok=False
- `ec-060` 期望=refuse 实际=answer ok=False
- `ec-058` 期望=refuse 实际=answer ok=False