# 评测报告 — a2

## 环境
- 模型：`qwen3.8-flash`  temperature=0.0
- Prompt 指纹：`c1038e268edf`
- 数据集：`data\benchmarks\ecommerce_v0.jsonl`，共 60 题（可判定 43 题）
- 开始时间：2026-10-30 21:38:46

## 汇总

| 指标 | 值 |
| --- | --- |
| EX（无序，分母=全部 43 道可判定题） | 83.72% |
| 排序题 EX（有序，分母=34 道 order_sensitive 题） | 82.35% |
| Schema 召回率 | 88.37% |
| 平均输入 token | 1348 |
| SQL/执行错误率 | 0.00% |
| 特殊题行为正确率 | 0.00% |
| 延迟 P50 / P95 | 27811 / 151003 ms |
| 单题成本 | ¥0.007886 |
| 总成本 | ¥0.4732 |
| 平均 LLM 调用次数 | 2.08 |
| 首轮正确率 | 79.07% |
| 修复增益 | 4.65% |
| 触发检索扩大次数 | 3 |

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
| join | 7 | 7 | 85.7% |
| nested | 21 | 21 | 81.0% |
| simple | 1 | 1 | 100.0% |

## 失败清单（前 20 条）

- `ec-005` [aggregation] 计算每个商品的平均评分，保留一位小数，返回平均评分最高的前 40 个商品（商品编号和平均分），按平均分降序。
  - status=ok  error=None
  - 生成 SQL：`WITH avg_reviews AS (SELECT product_id, ROUND(AVG(rating), 1) AS avg_rating FROM reviews GROUP BY product_id), ranked AS (SELECT product_id, avg_rating, ROW_NUMBER() OVER (ORDER BY avg_rating DESC, pr`
  - 差异：row_diff only_pred=[('58.00', '3.50')] only_gold=[('129.00', '3.50')]
- `ec-008` [aggregation] 计算每个城市的成交额占全库总 GMV 的百分比，返回城市和占比（百分比数值，保留两位小数）两列，按占比降序。
  - status=ok  error=None
  - 生成 SQL：`WITH paid_orders AS (SELECT u.city AS city FROM orders AS o JOIN users AS u ON u.user_id = o.user_id WHERE o.status IN ('paid','shipped','completed')) SELECT city AS `城市`, ROUND(100.0 * COUNT(*) / NUL`
  - 差异：row_diff only_pred=[('北京', '19.13'), ('深圳', '18.60'), ('杭州', '15.93')] only_gold=[('北京', '19.22'), ('深圳', '18.04'), ('<NULL>', '16.19')]
- `ec-020` [join] 统计每个城市的成交总金额（GMV 口径），返回城市和总金额两列，按总金额降序。
  - status=ok  error=None
  - 生成 SQL：`SELECT u.city AS city, COUNT(o.order_id) AS total_amount FROM users AS u LEFT JOIN orders AS o ON o.user_id = u.user_id AND o.status IN ('paid','shipped','completed') GROUP BY u.city ORDER BY total_am`
  - 差异：row_diff only_pred=[('北京', '436.00'), ('深圳', '424.00'), ('杭州', '363.00')] only_gold=[('北京', '1065925.00'), ('深圳', '1000622.50'), ('<NULL>', '897835.74')]
- `ec-031` [nested] 用 WITH 计算每个用户的成交总额，返回累计消费最高的前 5 名用户（用户名和累计金额），按金额降序。
  - status=ok  error=None
  - 生成 SQL：`WITH user_gmv AS (
  SELECT
    u.user_id,
    u.username,
    COUNT(o.order_id) AS total_amount
  FROM users u
  LEFT JOIN orders o
    ON o.user_id = u.user_id
   AND o.status IN ('paid', 'shipped',`
  - 差异：row_diff only_pred=[('user310', '13.00'), ('user235', '12.00'), ('user421', '12.00')] only_gold=[('user235', '35096.70'), ('user310', '34675.40'), ('user268', '32178.48')]
- `ec-033` [nested] 找出每个用户的第一笔成交订单（按时间最早），返回首笔订单金额最高的前 5 名用户的用户名和首笔金额，按金额降序。
  - status=ok  error=None
  - 生成 SQL：`WITH first_orders AS (SELECT user_id, order_id, ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY created_at ASC, order_id ASC) AS rn FROM orders WHERE status IN ('paid','shipped','completed')), first_`
  - 差异：row_diff only_pred=[('user478', '<NULL>'), ('user056', '<NULL>'), ('user053', '<NULL>')] only_gold=[('user355', '7019.87'), ('user423', '6898.74'), ('user270', '6885.17')]
- `ec-042` [nested] 统计每个一级分类（parent_id 为空）下所有二级子分类商品的在库总数量（只统计直接挂靠在二级分类下的商品，不含一级分类自身直接挂靠的商品），返回分类名称和商品总数两列，按商品总数降序；总数相同时按分类编号升序。
  - status=ok  error=None
  - 生成 SQL：`WITH product_stock AS (SELECT product_id, SUM(change) AS stock_qty FROM inventory_logs GROUP BY product_id) SELECT c1.name AS category_name, COALESCE(SUM(COALESCE(ps.stock_qty, 0)), 0) AS total_stock_`
  - 差异：row_diff only_pred=[('家电', '6781.00'), ('数码', '3658.00'), ('服饰', '3317.00')] only_gold=[('家电', '61.00'), ('数码', '43.00'), ('服饰', '36.00')]
- `ec-038` [nested] 计算复购用户（成交订单数不少于 2 的用户）的平均客单价，即这些用户各自客单价的平均值，保留两位小数，返回单个数值。
  - status=ok  error=None
  - 生成 SQL：`SELECT ROUND(NULL, 2) AS avg_customer_order_value;`
  - 差异：row_diff only_pred=[('<NULL>',)] only_gold=[('2421.73',)]

## 特殊题明细（澄清 / 拒绝）

- `ec-044` 期望=clarify 实际=answer ok=False
- `ec-047` 期望=clarify 实际=answer ok=False
- `ec-046` 期望=clarify 实际=answer ok=False
- `ec-045` 期望=clarify 实际=answer ok=False
- `ec-048` 期望=clarify 实际=answer ok=False
- `ec-049` 期望=clarify 实际=answer ok=False
- `ec-051` 期望=clarify 实际=answer ok=False
- `ec-052` 期望=clarify 实际=answer ok=False
- `ec-053` 期望=clarify 实际=answer ok=False
- `ec-050` 期望=clarify 实际=answer ok=False
- `ec-054` 期望=refuse 实际=answer ok=False
- `ec-056` 期望=refuse 实际=answer ok=False
- `ec-057` 期望=refuse 实际=answer ok=False
- `ec-055` 期望=refuse 实际=answer ok=False
- `ec-059` 期望=refuse 实际=answer ok=False
- `ec-060` 期望=refuse 实际=answer ok=False
- `ec-058` 期望=refuse 实际=answer ok=False