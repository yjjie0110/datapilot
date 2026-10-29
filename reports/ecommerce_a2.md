# 评测报告 — a2

## 环境
- 模型：`qwen3.8-flash`  temperature=0.0
- Prompt 指纹：`a32cc524ca69`
- 数据集：`data\benchmarks\ecommerce_v0.jsonl`，共 60 题（可判定 43 题）
- 开始时间：2026-10-29 12:13:41

## 汇总

| 指标 | 值 |
| --- | --- |
| EX（无序，分母=全部 43 道可判定题） | 86.05% |
| 排序题 EX（有序，分母=37 道 order_sensitive 题） | 83.78% |
| Schema 召回率 | 93.02% |
| 平均输入 token | 726 |
| SQL/执行错误率 | 0.00% |
| 特殊题行为正确率 | 0.00% |
| 延迟 P50 / P95 | 7659 / 47497 ms |
| 单题成本 | ¥0.002672 |
| 总成本 | ¥0.1603 |
| 平均 LLM 调用次数 | 1.07 |
| 首轮正确率 | 83.72% |
| 修复增益 | 2.33% |
| 触发检索扩大次数 | 2 |

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
| aggregation | 12 | 12 | 75.0% |
| ambiguous | 10 | 0 | - |
| join | 12 | 12 | 83.3% |
| nested | 9 | 9 | 88.9% |
| simple | 10 | 10 | 100.0% |

## 失败清单（前 20 条）

- `ec-015` [aggregation] 找出成交订单数最多的前 10 名用户，返回用户编号和成交订单数两列，按订单数降序。
  - status=ok  error=None
  - 生成 SQL：`SELECT user_id, COUNT(order_id) AS order_count FROM orders WHERE status IN ('paid', 'shipped', 'completed') GROUP BY user_id ORDER BY order_count DESC LIMIT 10;`
  - 差异：row_diff only_pred=[('373.00', '10.00'), ('337.00', '10.00')] only_gold=[('80.00', '10.00'), ('232.00', '10.00')]
- `ec-017` [aggregation] 计算每个商品的平均评分，保留一位小数，返回平均评分最高的前 10 个商品（商品编号和平均分），按平均分降序。
  - status=ok  error=None
  - 生成 SQL：`SELECT product_id, ROUND(AVG(rating), 1) AS avg_rating FROM reviews GROUP BY product_id ORDER BY avg_rating DESC LIMIT 10;`
  - 差异：row_diff only_pred=[('178.00', '4.00'), ('121.00', '4.00')] only_gold=[('9.00', '4.00'), ('18.00', '4.00')]
- `ec-020` [aggregation] 统计每个商品被购买的总数量（order_items 的 quantity 求和），取总量前 3 的商品（编号和总量），按总量降序。
  - status=ok  error=None
  - 生成 SQL：`SELECT oi.product_id, SUM(oi.quantity) AS total_quantity FROM order_items AS oi JOIN orders AS o ON oi.order_id = o.order_id WHERE o.status IN ('paid','shipped','completed') GROUP BY oi.product_id ORD`
  - 差异：row_diff only_pred=[('104.00', '89.00'), ('23.00', '84.00'), ('119.00', '83.00')] only_gold=[('104.00', '112.00'), ('46.00', '109.00'), ('81.00', '108.00')]
- `ec-030` [join] 列出使用过优惠券的订单中支付金额最高的前 50 个，返回订单编号、优惠券编码、折扣率三列，按订单编号升序。
  - status=ok  error=None
  - 生成 SQL：`SELECT o.order_id AS `订单编号`, o.coupon_id AS `优惠券编码`, NULL AS `折扣率` FROM orders AS o WHERE o.coupon_id IS NOT NULL AND o.status IN ('paid', 'shipped', 'completed') ORDER BY o.order_id ASC LIMIT 50;`
  - 差异：row_diff only_pred=[('19.00', '20.00', '<NULL>'), ('22.00', '18.00', '<NULL>'), ('27.00', '9.00', '<NULL>')] only_gold=[('19.00', 'CP020', '15.00'), ('22.00', 'CP018', '20.00'), ('27.00', 'CP009', '15.00')]
- `ec-043` [nested] 用 WITH 计算每个用户的成交总额，返回累计消费最高的前 5 名用户（用户名和累计金额），按金额降序。
  - status=ok  error=None
  - 生成 SQL：`WITH transaction_orders AS (SELECT user_id FROM orders WHERE status IN ('paid','shipped','completed')), user_totals AS (SELECT user_id, SUM(0) AS cumulative_amount FROM transaction_orders GROUP BY use`
  - 差异：row_diff only_pred=[('user001', '0.00'), ('user002', '0.00'), ('user003', '0.00')] only_gold=[('user235', '35096.70'), ('user310', '34675.40'), ('user268', '32178.48')]
- `ec-032` [join] 统计每个城市的成交总金额（GMV 口径），返回城市和总金额两列，按总金额降序。
  - status=ok  error=None
  - 生成 SQL：`SELECT u.city, SUM(NULL) AS total_gmv FROM orders o JOIN users u ON o.user_id = u.user_id WHERE o.status IN ('paid', 'shipped', 'completed') GROUP BY u.city ORDER BY total_gmv DESC`
  - 差异：row_diff only_pred=[('深圳', '<NULL>'), ('杭州', '<NULL>'), ('成都', '<NULL>')] only_gold=[('北京', '1065925.00'), ('深圳', '1000622.50'), ('<NULL>', '897835.74')]

## 特殊题明细（澄清 / 拒绝）

- `ec-044` 期望=clarify 实际=answer ok=False
- `ec-045` 期望=clarify 实际=answer ok=False
- `ec-046` 期望=clarify 实际=answer ok=False
- `ec-047` 期望=clarify 实际=answer ok=False
- `ec-048` 期望=clarify 实际=answer ok=False
- `ec-049` 期望=clarify 实际=answer ok=False
- `ec-052` 期望=clarify 实际=answer ok=False
- `ec-051` 期望=clarify 实际=answer ok=False
- `ec-050` 期望=clarify 实际=answer ok=False
- `ec-053` 期望=clarify 实际=answer ok=False
- `ec-054` 期望=refuse 实际=answer ok=False
- `ec-056` 期望=refuse 实际=answer ok=False
- `ec-057` 期望=refuse 实际=answer ok=False
- `ec-060` 期望=refuse 实际=answer ok=False
- `ec-059` 期望=refuse 实际=answer ok=False
- `ec-055` 期望=refuse 实际=answer ok=False
- `ec-058` 期望=refuse 实际=answer ok=False