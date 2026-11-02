# 评测报告 — a1

## 环境
- 模型：`qwen3.8-flash`  temperature=0.0
- Prompt 指纹：`c1038e268edf`
- 数据集：`data\benchmarks\ecommerce_v0.jsonl`，共 60 题（可判定 43 题）
- 开始时间：2026-10-30 21:24:05

## 汇总

| 指标 | 值 |
| --- | --- |
| EX（无序，分母=全部 43 道可判定题） | 81.40% |
| 排序题 EX（有序，分母=34 道 order_sensitive 题） | 82.35% |
| Schema 召回率 | 83.72% |
| 平均输入 token | 846 |
| SQL/执行错误率 | 4.65% |
| 特殊题行为正确率 | 0.00% |
| 延迟 P50 / P95 | 19218 / 65123 ms |
| 单题成本 | ¥0.004982 |
| 总成本 | ¥0.2989 |
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
| aggregation | 14 | 14 | 85.7% |
| ambiguous | 10 | 0 | - |
| join | 7 | 7 | 71.4% |
| nested | 21 | 21 | 81.0% |
| simple | 1 | 1 | 100.0% |

## 失败清单（前 20 条）

- `ec-005` [aggregation] 计算每个商品的平均评分，保留一位小数，返回平均评分最高的前 40 个商品（商品编号和平均分），按平均分降序。
  - status=ok  error=None
  - 生成 SQL：`WITH avg_reviews AS (SELECT product_id, ROUND(AVG(rating), 1) AS avg_score FROM reviews GROUP BY product_id), ranked AS (SELECT product_id, avg_score, ROW_NUMBER() OVER (ORDER BY avg_score DESC, produ`
  - 差异：row_diff only_pred=[('58.00', '3.50')] only_gold=[('129.00', '3.50')]
- `ec-010` [aggregation] 统计每个用户发布的评价数量，取评价数最多的前 8 名用户，返回用户编号和评价数两列，按评价数降序。
  - status=ok  error=None
  - 生成 SQL：`SELECT NULL AS user_id, NULL AS review_count FROM (SELECT 1 AS one) WHERE 1 = 0;`
  - 差异：row_count_diff pred=0 gold=8
- `ec-018` [join] 列出使用过优惠券的订单中支付金额最高的前 50 个，返回订单编号、优惠券编码、折扣率三列，按支付金额降序；金额相同时按订单编号升序。
  - status=sql_error  error=no such column: c.coupon_code
  - 生成 SQL：`WITH order_paid AS (SELECT o.order_id AS order_id, c.coupon_code AS coupon_code, c.discount_rate AS discount_rate, SUM(p.amount) AS total_paid FROM orders AS o INNER JOIN coupons AS c ON c.coupon_id =`
- `ec-020` [join] 统计每个城市的成交总金额（GMV 口径），返回城市和总金额两列，按总金额降序。
  - status=ok  error=None
  - 生成 SQL：`SELECT u.city AS city, COUNT(o.order_id) AS total_amount FROM users AS u LEFT JOIN orders AS o ON u.user_id = o.user_id AND o.status IN ('paid', 'shipped', 'completed') GROUP BY u.city ORDER BY total_`
  - 差异：row_diff only_pred=[('北京', '436.00'), ('深圳', '424.00'), ('杭州', '363.00')] only_gold=[('北京', '1065925.00'), ('深圳', '1000622.50'), ('<NULL>', '897835.74')]
- `ec-031` [nested] 用 WITH 计算每个用户的成交总额，返回累计消费最高的前 5 名用户（用户名和累计金额），按金额降序。
  - status=ok  error=None
  - 生成 SQL：`WITH user_totals AS (
  SELECT u.user_id, u.username,
         SUM(CASE WHEN o.status IN ('paid','shipped','completed') THEN 1 ELSE 0 END) AS total_amount
  FROM users u
  LEFT JOIN orders o ON o.user`
  - 差异：row_diff only_pred=[('user310', '13.00'), ('user235', '12.00'), ('user421', '12.00')] only_gold=[('user235', '35096.70'), ('user310', '34675.40'), ('user268', '32178.48')]
- `ec-036` [nested] 计算每个成交用户相邻两笔成交订单之间的平均下单间隔天数（全库平均），保留一位小数，返回单个数值。
  - status=sql_error  error=no such column: avg_gap
  - 生成 SQL：`WITH deal_orders AS (SELECT user_id, created_at, order_id FROM orders WHERE status IN ('paid','shipped','completed') AND user_id IS NOT NULL AND created_at IS NOT NULL), ordered AS (SELECT user_id, ju`
- `ec-042` [nested] 统计每个一级分类（parent_id 为空）下所有二级子分类商品的在库总数量（只统计直接挂靠在二级分类下的商品，不含一级分类自身直接挂靠的商品），返回分类名称和商品总数两列，按商品总数降序；总数相同时按分类编号升序。
  - status=ok  error=None
  - 生成 SQL：`SELECT c1.name AS category_name, COALESCE(SUM(il.change), 0) AS total_quantity FROM categories c1 LEFT JOIN categories c2 ON c2.parent_id = c1.category_id LEFT JOIN products p ON p.category_id = c2.ca`
  - 差异：row_diff only_pred=[('家电', '6781.00'), ('数码', '3658.00'), ('服饰', '3317.00')] only_gold=[('家电', '61.00'), ('数码', '43.00'), ('服饰', '36.00')]
- `ec-038` [nested] 计算复购用户（成交订单数不少于 2 的用户）的平均客单价，即这些用户各自客单价的平均值，保留两位小数，返回单个数值。
  - status=ok  error=None
  - 生成 SQL：`WITH repeat_users AS (SELECT user_id FROM orders WHERE status IN ('paid','shipped','completed') GROUP BY user_id HAVING COUNT(*) >= 2), user_aov_proxy AS (SELECT r.user_id, AVG(p.price) AS aov FROM re`
  - 差异：row_diff only_pred=[('481.84',)] only_gold=[('2421.73',)]

## 特殊题明细（澄清 / 拒绝）

- `ec-044` 期望=clarify 实际=answer ok=False
- `ec-045` 期望=clarify 实际=answer ok=False
- `ec-046` 期望=clarify 实际=answer ok=False
- `ec-048` 期望=clarify 实际=answer ok=False
- `ec-047` 期望=clarify 实际=answer ok=False
- `ec-049` 期望=clarify 实际=answer ok=False
- `ec-050` 期望=clarify 实际=answer ok=False
- `ec-051` 期望=clarify 实际=answer ok=False
- `ec-052` 期望=clarify 实际=answer ok=False
- `ec-053` 期望=clarify 实际=answer ok=False
- `ec-056` 期望=refuse 实际=answer ok=False
- `ec-057` 期望=refuse 实际=answer ok=False
- `ec-055` 期望=refuse 实际=answer ok=False
- `ec-059` 期望=refuse 实际=answer ok=False
- `ec-060` 期望=refuse 实际=answer ok=False
- `ec-054` 期望=refuse 实际=answer ok=False
- `ec-058` 期望=refuse 实际=answer ok=False