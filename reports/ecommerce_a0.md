# 评测报告 — a0

## 环境
- 模型：`qwen3.8-flash`  temperature=0.0
- Prompt 指纹：`a7d099e8ee30`
- 数据集：`data\benchmarks\ecommerce_v0.jsonl`，共 60 题（可判定 43 题）
- 开始时间：2026-10-29 19:09:27

## 汇总

| 指标 | 值 |
| --- | --- |
| EX（无序，分母=全部 43 道可判定题） | 79.07% |
| 排序题 EX（有序，分母=34 道 order_sensitive 题） | 73.53% |
| Schema 召回率 | N/A |
| 平均输入 token | N/A |
| SQL/执行错误率 | 0.00% |
| 特殊题行为正确率 | 0.00% |
| 延迟 P50 / P95 | 18333 / 70212 ms |
| 单题成本 | ¥0.003807 |
| 总成本 | ¥0.2284 |
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
| aggregation | 14 | 14 | 42.9% |
| ambiguous | 10 | 0 | - |
| join | 7 | 7 | 100.0% |
| nested | 21 | 21 | 95.2% |
| simple | 1 | 1 | 100.0% |

## 失败清单（前 20 条）

- `ec-004` [aggregation] 统计每个商品的评价数量，取评价数最多的前 13 个商品，返回商品编号和评价数两列，按评价数降序。
  - status=ok  error=None
  - 生成 SQL：`SELECT product_id, COUNT(*) AS review_count FROM reviews GROUP BY product_id ORDER BY review_count DESC LIMIT 13;`
  - 差异：row_diff only_pred=[('150.00', '10.00')] only_gold=[('5.00', '10.00')]
- `ec-003` [aggregation] 找出成交订单数最多的前 10 名用户，返回用户编号和成交订单数两列，按订单数降序。
  - status=ok  error=None
  - 生成 SQL：`SELECT user_id, COUNT(*) AS order_count FROM orders WHERE status IN ('paid','shipped','completed') GROUP BY user_id ORDER BY order_count DESC LIMIT 10;`
  - 差异：row_diff only_pred=[('373.00', '10.00'), ('337.00', '10.00')] only_gold=[('80.00', '10.00'), ('232.00', '10.00')]
- `ec-005` [aggregation] 计算每个商品的平均评分，保留一位小数，返回平均评分最高的前 40 个商品（商品编号和平均分），按平均分降序。
  - status=ok  error=None
  - 生成 SQL：`SELECT product_id, ROUND(AVG(rating), 1) AS avg_rating FROM reviews GROUP BY product_id ORDER BY avg_rating DESC LIMIT 40;`
  - 差异：row_diff only_pred=[('181.00', '3.50'), ('170.00', '3.50'), ('164.00', '3.50')] only_gold=[('129.00', '3.50'), ('29.00', '3.50'), ('31.00', '3.50')]
- `ec-010` [aggregation] 统计每个用户发布的评价数量，取评价数最多的前 8 名用户，返回用户编号和评价数两列，按评价数降序。
  - status=ok  error=None
  - 生成 SQL：`SELECT user_id, COUNT(review_id) AS review_count FROM reviews GROUP BY user_id ORDER BY review_count DESC LIMIT 8;`
  - 差异：row_diff only_pred=[('477.00', '6.00'), ('450.00', '6.00'), ('417.00', '6.00')] only_gold=[('12.00', '6.00'), ('39.00', '6.00'), ('129.00', '6.00')]
- `ec-002` [aggregation] 统计每个一级分类（parent_id 为空的分类）下在售商品的数量，按数量降序；用分类名输出。
  - status=ok  error=None
  - 生成 SQL：`WITH RECURSIVE category_tree AS (SELECT c.category_id AS root_id, c.name AS root_name, c.category_id AS category_id FROM categories c WHERE c.parent_id IS NULL UNION ALL SELECT ct.root_id, ct.root_nam`
  - 差异：row_diff only_pred=[('家电', '73.00'), ('数码', '54.00'), ('服饰', '53.00')] only_gold=[('服饰', '21.00'), ('家电', '18.00'), ('数码', '14.00')]
- `ec-013` [aggregation] 找出成交订单数最多的前 15 名用户，返回用户编号和成交订单数两列，按订单数降序。
  - status=ok  error=None
  - 生成 SQL：`SELECT user_id, COUNT(order_id) AS completed_order_count FROM orders WHERE user_id IS NOT NULL AND status IN ('paid','shipped','completed') GROUP BY user_id ORDER BY completed_order_count DESC LIMIT 1`
  - 差异：row_diff only_pred=[('491.00', '9.00'), ('402.00', '9.00'), ('349.00', '9.00')] only_gold=[('4.00', '9.00'), ('21.00', '9.00'), ('82.00', '9.00')]
- `ec-016` [aggregation] 统计每个商品在成交订单中被购买的总数量（order_items.quantity 求和），返回总量最多的前 25 个商品（商品编号和总量），按总量降序。
  - status=ok  error=None
  - 生成 SQL：`SELECT oi.product_id, SUM(oi.quantity) AS total_quantity FROM order_items AS oi JOIN orders AS o ON oi.order_id = o.order_id WHERE o.status IN ('paid','shipped','completed') GROUP BY oi.product_id ORD`
  - 差异：row_diff only_pred=[('200.00', '69.00')] only_gold=[('47.00', '69.00')]
- `ec-022` [aggregation] 统计每个商品成交的订单笔数（同一订单内同一商品只算一笔，order_items 去重订单），返回成交订单笔数最多的前 45 个商品（商品编号和订单笔数），按笔数降序。
  - status=ok  error=None
  - 生成 SQL：`SELECT oi.product_id, COUNT(DISTINCT oi.order_id) AS order_count FROM order_items AS oi JOIN orders AS o ON o.order_id = oi.order_id WHERE o.status IN ('paid','shipped','completed') GROUP BY oi.produc`
  - 差异：row_diff only_pred=[('180.00', '32.00')] only_gold=[('16.00', '32.00')]
- `ec-042` [nested] 统计每个一级分类（parent_id 为空）下所有二级子分类商品的在库总数量（只统计直接挂靠在二级分类下的商品，不含一级分类自身直接挂靠的商品），返回分类名称和商品总数两列，按商品总数降序；总数相同时按分类编号升序。
  - status=ok  error=None
  - 生成 SQL：`WITH first_level AS (SELECT category_id, name FROM categories WHERE parent_id IS NULL), second_level AS (SELECT c.category_id AS second_category_id, f.category_id AS first_category_id FROM categories `
  - 差异：row_diff only_pred=[('家电', '48.00'), ('数码', '37.00'), ('服饰', '29.00')] only_gold=[('家电', '61.00'), ('数码', '43.00'), ('服饰', '36.00')]

## 特殊题明细（澄清 / 拒绝）

- `ec-044` 期望=clarify 实际=answer ok=False
- `ec-045` 期望=clarify 实际=answer ok=False
- `ec-048` 期望=clarify 实际=answer ok=False
- `ec-047` 期望=clarify 实际=answer ok=False
- `ec-049` 期望=clarify 实际=answer ok=False
- `ec-051` 期望=clarify 实际=answer ok=False
- `ec-052` 期望=clarify 实际=answer ok=False
- `ec-050` 期望=clarify 实际=answer ok=False
- `ec-046` 期望=clarify 实际=answer ok=False
- `ec-054` 期望=refuse 实际=answer ok=False
- `ec-055` 期望=refuse 实际=answer ok=False
- `ec-053` 期望=clarify 实际=answer ok=False
- `ec-057` 期望=refuse 实际=answer ok=False
- `ec-059` 期望=refuse 实际=answer ok=False
- `ec-058` 期望=refuse 实际=answer ok=False
- `ec-060` 期望=refuse 实际=answer ok=False
- `ec-056` 期望=refuse 实际=answer ok=False