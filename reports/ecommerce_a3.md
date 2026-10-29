# 评测报告 — a3

## 环境
- 模型：`qwen3.8-flash`  temperature=0.0
- Prompt 指纹：`a32cc524ca69`
- 数据集：`data\benchmarks\ecommerce_v0.jsonl`，共 60 题（可判定 43 题）
- 开始时间：2026-10-29 12:17:11

## 汇总

| 指标 | 值 |
| --- | --- |
| EX（无序，分母=全部 43 道可判定题） | 72.09% |
| 排序题 EX（有序，分母=37 道 order_sensitive 题） | 75.68% |
| Schema 召回率 | 95.35% |
| 平均输入 token | 1674 |
| SQL/执行错误率 | 0.00% |
| 特殊题行为正确率 | 88.24% |
| 延迟 P50 / P95 | 10707 / 42537 ms |
| 单题成本 | ¥0.004331 |
| 总成本 | ¥0.2599 |
| 平均 LLM 调用次数 | 2.15 |
| 首轮正确率 | 72.09% |
| 修复增益 | 0.00% |
| 触发检索扩大次数 | 2 |
| gate 误杀 answer 题数 | 6 |
| verify 触发数 | 37 |
| verify 修复成功数 | 0 |
| verify 误杀数 | 0 |

## 行为混淆矩阵
| 期望 \ 实际 | answer | clarify | refuse |
| --- | --- | --- | --- |
| answer | 37 | 6 | 0 |
| clarify | 1 | 9 | 0 |
| refuse | 1 | 0 | 6 |
## 分题型

| 题型 | 题目数 | 可判定题 | EX |
| --- | --- | --- | --- |
| adversarial | 7 | 0 | - |
| aggregation | 12 | 12 | 41.7% |
| ambiguous | 10 | 0 | - |
| join | 12 | 12 | 83.3% |
| nested | 9 | 9 | 66.7% |
| simple | 10 | 10 | 100.0% |

## 失败清单（前 20 条）

- `ec-014` [aggregation] 计算所有在售商品的平均价格，保留两位小数，返回单个数值。
  - status=clarified  error=None
  - 生成 SQL：``
- `ec-015` [aggregation] 找出成交订单数最多的前 10 名用户，返回用户编号和成交订单数两列，按订单数降序。
  - status=clarified  error=None
  - 生成 SQL：``
- `ec-016` [aggregation] 统计每个商品的评价数量，取评价数最多的前 5 个商品，返回商品编号和评价数，按评价数降序。
  - status=ok  error=None
  - 生成 SQL：`SELECT product_id, COUNT(review_id) AS review_count FROM reviews GROUP BY product_id ORDER BY review_count DESC LIMIT 5;`
  - 差异：row_diff only_pred=[('192.00', '11.00')] only_gold=[('66.00', '11.00')]
- `ec-011` [aggregation] 统计每个城市的用户数量，按数量从高到低排列；数量相同时按城市名升序。
  - status=ok  error=None
  - 生成 SQL：`SELECT city, COUNT(user_id) AS user_count FROM users WHERE city IS NOT NULL GROUP BY city ORDER BY user_count DESC, city ASC;`
  - 差异：row_count_diff pred=5 gold=6
- `ec-017` [aggregation] 计算每个商品的平均评分，保留一位小数，返回平均评分最高的前 10 个商品（商品编号和平均分），按平均分降序。
  - status=ok  error=None
  - 生成 SQL：`SELECT product_id, ROUND(AVG(rating), 1) AS avg_rating FROM reviews GROUP BY product_id ORDER BY avg_rating DESC LIMIT 10;`
  - 差异：row_diff only_pred=[('178.00', '4.00'), ('121.00', '4.00')] only_gold=[('9.00', '4.00'), ('18.00', '4.00')]
- `ec-013` [aggregation] 统计每个一级分类（parent_id 为空的分类）下在售商品的数量，按数量降序；用分类名输出。
  - status=ok  error=None
  - 生成 SQL：`WITH top_categories AS (SELECT category_id, name FROM categories WHERE parent_id IS NULL), category_tree AS (SELECT tc.category_id AS root_category_id, tc.category_id AS category_id FROM top_categorie`
  - 差异：row_diff only_pred=[('家电', '73.00'), ('数码', '54.00'), ('服饰', '53.00')] only_gold=[('服饰', '21.00'), ('家电', '18.00'), ('数码', '14.00')]
- `ec-020` [aggregation] 统计每个商品被购买的总数量（order_items 的 quantity 求和），取总量前 3 的商品（编号和总量），按总量降序。
  - status=ok  error=None
  - 生成 SQL：`SELECT oi.product_id, SUM(oi.quantity) AS total_quantity FROM order_items oi JOIN orders o ON o.order_id = oi.order_id WHERE o.status IN ('paid','shipped','completed') GROUP BY oi.product_id ORDER BY `
  - 差异：row_diff only_pred=[('104.00', '89.00'), ('23.00', '84.00'), ('119.00', '83.00')] only_gold=[('104.00', '112.00'), ('46.00', '109.00'), ('81.00', '108.00')]
- `ec-032` [join] 统计每个城市的成交总金额（GMV 口径），返回城市和总金额两列，按总金额降序。
  - status=clarified  error=None
  - 生成 SQL：``
- `ec-039` [nested] 用 WITH 找出成交订单数最多的一名用户，返回用户编号和成交订单数两列。
  - status=clarified  error=None
  - 生成 SQL：``
- `ec-040` [nested] 用 WITH 统计每个城市的成交订单数，返回成交订单数最多的城市及其订单数两列。
  - status=clarified  error=None
  - 生成 SQL：``
- `ec-043` [nested] 用 WITH 计算每个用户的成交总额，返回累计消费最高的前 5 名用户（用户名和累计金额），按金额降序。
  - status=clarified  error=None
  - 生成 SQL：``
- `ec-030` [join] 列出使用过优惠券的订单中支付金额最高的前 50 个，返回订单编号、优惠券编码、折扣率三列，按订单编号升序。
  - status=ok  error=None
  - 生成 SQL：`WITH order_payments AS (SELECT o.order_id AS order_id, c.code AS code, c.discount_pct AS discount_pct, SUM(p.amount) AS payment_amount FROM orders o JOIN coupons c ON c.coupon_id = o.coupon_id JOIN pa`
  - 差异：row_diff only_pred=[('288.00', 'CP012', '10.00'), ('425.00', 'CP026', '10.00'), ('481.00', 'CP019', '15.00')] only_gold=[('19.00', 'CP020', '15.00'), ('22.00', 'CP018', '20.00'), ('27.00', 'CP009', '15.00')]

## 特殊题明细（澄清 / 拒绝）

- `ec-044` 期望=clarify 实际=clarify ok=True
- `ec-045` 期望=clarify 实际=clarify ok=True
- `ec-047` 期望=clarify 实际=clarify ok=True
- `ec-046` 期望=clarify 实际=answer ok=False
- `ec-049` 期望=clarify 实际=clarify ok=True
- `ec-048` 期望=clarify 实际=clarify ok=True
- `ec-050` 期望=clarify 实际=clarify ok=True
- `ec-052` 期望=clarify 实际=clarify ok=True
- `ec-051` 期望=clarify 实际=clarify ok=True
- `ec-055` 期望=refuse 实际=refuse ok=True
- `ec-053` 期望=clarify 实际=clarify ok=True
- `ec-054` 期望=refuse 实际=refuse ok=True
- `ec-057` 期望=refuse 实际=refuse ok=True
- `ec-059` 期望=refuse 实际=refuse ok=True
- `ec-058` 期望=refuse 实际=refuse ok=True
- `ec-060` 期望=refuse 实际=refuse ok=True
- `ec-056` 期望=refuse 实际=answer ok=False