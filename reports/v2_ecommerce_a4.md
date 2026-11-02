# 评测报告 — a4

## 环境
- 模型：`qwen3.8-flash`  temperature=0.0
- Prompt 指纹：`c1038e268edf`
- 数据集：`data\benchmarks\ecommerce_v0.jsonl`，共 60 题（可判定 43 题）
- 开始时间：2026-10-30 22:27:00

## 汇总

| 指标 | 值 |
| --- | --- |
| EX（无序，分母=全部 43 道可判定题） | 86.05% |
| 排序题 EX（有序，分母=34 道 order_sensitive 题） | 82.35% |
| Schema 召回率 | 90.70% |
| 平均输入 token | 2357 |
| SQL/执行错误率 | 0.00% |
| 特殊题行为正确率 | 70.59% |
| 延迟 P50 / P95 | 25068 / 95344 ms |
| 单题成本 | ¥0.007972 |
| 总成本 | ¥0.4783 |
| 平均 LLM 调用次数 | 2.78 |
| 首轮正确率 | 79.07% |
| 修复增益 | 6.98% |
| 触发检索扩大次数 | 4 |
| gate 误杀 answer 题数 | 0 |
| verify 触发数 | 43 |
| verify 修复成功数 | 0 |
| verify 误杀数 | 0 |

## 行为混淆矩阵
| 期望 \ 实际 | answer | clarify | refuse |
| --- | --- | --- | --- |
| answer | 43 | 0 | 0 |
| clarify | 4 | 6 | 0 |
| refuse | 1 | 0 | 6 |
## 分题型

| 题型 | 题目数 | 可判定题 | EX |
| --- | --- | --- | --- |
| adversarial | 7 | 0 | - |
| aggregation | 14 | 14 | 78.6% |
| ambiguous | 10 | 0 | - |
| join | 7 | 7 | 85.7% |
| nested | 21 | 21 | 90.5% |
| simple | 1 | 1 | 100.0% |

## 失败清单（前 20 条）

- `ec-005` [aggregation] 计算每个商品的平均评分，保留一位小数，返回平均评分最高的前 40 个商品（商品编号和平均分），按平均分降序。
  - status=ok  error=None
  - 生成 SQL：`WITH product_avg AS (SELECT p.product_id, ROUND(AVG(r.rating), 1) AS avg_rating FROM products p JOIN reviews r ON p.product_id = r.product_id GROUP BY p.product_id), ranked AS (SELECT product_id, avg_`
  - 差异：row_diff only_pred=[('58.00', '3.50')] only_gold=[('129.00', '3.50')]
- `ec-002` [aggregation] 统计每个一级分类（parent_id 为空的分类）下在售商品的数量，按数量降序；用分类名输出。
  - status=ok  error=None
  - 生成 SQL：`WITH RECURSIVE category_tree AS (SELECT category_id, name, category_id AS root_category_id, name AS root_category_name FROM categories WHERE parent_id IS NULL UNION ALL SELECT c.category_id, c.name, c`
  - 差异：row_diff only_pred=[('家电', '73.00'), ('数码', '54.00'), ('服饰', '53.00')] only_gold=[('服饰', '21.00'), ('家电', '18.00'), ('数码', '14.00')]
- `ec-008` [aggregation] 计算每个城市的成交额占全库总 GMV 的百分比，返回城市和占比（百分比数值，保留两位小数）两列，按占比降序。
  - status=ok  error=None
  - 生成 SQL：`WITH tx_orders AS (SELECT order_id, user_id FROM orders WHERE status IN ('paid','shipped','completed')), city_amount AS (SELECT u.city, COUNT(t.order_id) AS amount FROM users u LEFT JOIN tx_orders t O`
  - 差异：row_count_diff pred=5 gold=6
- `ec-020` [join] 统计每个城市的成交总金额（GMV 口径），返回城市和总金额两列，按总金额降序。
  - status=ok  error=None
  - 生成 SQL：`SELECT u.city AS city, 0 AS total_gmv FROM users u LEFT JOIN orders o ON o.user_id = u.user_id AND o.status IN ('paid','shipped','completed') GROUP BY u.city ORDER BY total_gmv DESC, u.city ASC`
  - 差异：row_diff only_pred=[('<NULL>', '0.00'), ('上海', '0.00'), ('北京', '0.00')] only_gold=[('北京', '1065925.00'), ('深圳', '1000622.50'), ('<NULL>', '897835.74')]
- `ec-031` [nested] 用 WITH 计算每个用户的成交总额，返回累计消费最高的前 5 名用户（用户名和累计金额），按金额降序。
  - status=ok  error=None
  - 生成 SQL：`WITH user_gmv AS (
  SELECT
    u.user_id,
    u.username,
    COUNT(o.order_id) AS cumulative_amount
  FROM users AS u
  JOIN orders AS o
    ON o.user_id = u.user_id
  WHERE o.status IN ('paid', 'sh`
  - 差异：row_diff only_pred=[('user310', '13.00'), ('user235', '12.00'), ('user421', '12.00')] only_gold=[('user235', '35096.70'), ('user310', '34675.40'), ('user268', '32178.48')]
- `ec-042` [nested] 统计每个一级分类（parent_id 为空）下所有二级子分类商品的在库总数量（只统计直接挂靠在二级分类下的商品，不含一级分类自身直接挂靠的商品），返回分类名称和商品总数两列，按商品总数降序；总数相同时按分类编号升序。
  - status=ok  error=None
  - 生成 SQL：`WITH product_stock AS (SELECT product_id, SUM(change) AS stock_qty FROM inventory_logs GROUP BY product_id) SELECT c.name AS category_name, COALESCE(SUM(ps.stock_qty), 0) AS total_stock FROM categorie`
  - 差异：row_diff only_pred=[('家电', '6781.00'), ('数码', '3658.00'), ('服饰', '3317.00')] only_gold=[('家电', '61.00'), ('数码', '43.00'), ('服饰', '36.00')]

## 特殊题明细（澄清 / 拒绝）

- `ec-045` 期望=clarify 实际=clarify ok=True
- `ec-044` 期望=clarify 实际=answer ok=False
- `ec-047` 期望=clarify 实际=answer ok=False
- `ec-050` 期望=clarify 实际=clarify ok=True
- `ec-049` 期望=clarify 实际=clarify ok=True
- `ec-046` 期望=clarify 实际=answer ok=False
- `ec-048` 期望=clarify 实际=clarify ok=True
- `ec-054` 期望=refuse 实际=refuse ok=True
- `ec-053` 期望=clarify 实际=clarify ok=True
- `ec-055` 期望=refuse 实际=refuse ok=True
- `ec-052` 期望=clarify 实际=clarify ok=True
- `ec-057` 期望=refuse 实际=refuse ok=True
- `ec-058` 期望=refuse 实际=refuse ok=True
- `ec-059` 期望=refuse 实际=refuse ok=True
- `ec-060` 期望=refuse 实际=refuse ok=True
- `ec-051` 期望=clarify 实际=answer ok=False
- `ec-056` 期望=refuse 实际=answer ok=False