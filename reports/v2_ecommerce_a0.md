# 评测报告 — a0

## 环境
- 模型：`qwen3.8-flash`  temperature=0.0
- Prompt 指纹：`c1038e268edf`
- 数据集：`data\benchmarks\ecommerce_v0.jsonl`，共 60 题（可判定 43 题）
- 开始时间：2026-10-30 21:12:01

## 汇总

| 指标 | 值 |
| --- | --- |
| EX（无序，分母=全部 43 道可判定题） | 88.37% |
| 排序题 EX（有序，分母=34 道 order_sensitive 题） | 88.24% |
| Schema 召回率 | N/A |
| 平均输入 token | N/A |
| SQL/执行错误率 | 0.00% |
| 特殊题行为正确率 | 0.00% |
| 延迟 P50 / P95 | 18435 / 72936 ms |
| 单题成本 | ¥0.004480 |
| 总成本 | ¥0.2688 |
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
| aggregation | 14 | 14 | 78.6% |
| ambiguous | 10 | 0 | - |
| join | 7 | 7 | 100.0% |
| nested | 21 | 21 | 90.5% |
| simple | 1 | 1 | 100.0% |

## 失败清单（前 20 条）

- `ec-005` [aggregation] 计算每个商品的平均评分，保留一位小数，返回平均评分最高的前 40 个商品（商品编号和平均分），按平均分降序。
  - status=ok  error=None
  - 生成 SQL：`WITH avg_reviews AS (SELECT product_id, ROUND(AVG(rating), 1) AS avg_rating FROM reviews GROUP BY product_id), ranked AS (SELECT product_id, avg_rating, ROW_NUMBER() OVER (ORDER BY avg_rating DESC, pr`
  - 差异：row_diff only_pred=[('58.00', '3.50')] only_gold=[('129.00', '3.50')]
- `ec-002` [aggregation] 统计每个一级分类（parent_id 为空的分类）下在售商品的数量，按数量降序；用分类名输出。
  - status=ok  error=None
  - 生成 SQL：`WITH RECURSIVE root_categories AS (SELECT category_id AS root_id, name AS root_name, category_id AS category_id FROM categories WHERE parent_id IS NULL UNION ALL SELECT rc.root_id, rc.root_name, c.cat`
  - 差异：row_diff only_pred=[('家电', '73.00'), ('数码', '54.00'), ('服饰', '53.00')] only_gold=[('服饰', '21.00'), ('家电', '18.00'), ('数码', '14.00')]
- `ec-008` [aggregation] 计算每个城市的成交额占全库总 GMV 的百分比，返回城市和占比（百分比数值，保留两位小数）两列，按占比降序。
  - status=ok  error=None
  - 生成 SQL：`WITH city_gmv AS (SELECT u.city AS city, COALESCE(SUM(CASE WHEN o.status IN ('paid','shipped','completed') THEN COALESCE(p.amount, 0) ELSE 0 END), 0) AS city_gmv FROM users u LEFT JOIN orders o ON o.u`
  - 差异：row_count_diff pred=5 gold=6
- `ec-036` [nested] 计算每个成交用户相邻两笔成交订单之间的平均下单间隔天数（全库平均），保留一位小数，返回单个数值。
  - status=ok  error=None
  - 生成 SQL：`WITH paid_orders AS (SELECT order_id, user_id, created_at FROM orders WHERE status IN ('paid','shipped','completed')), gaps AS (SELECT user_id, julianday(created_at) - julianday(LAG(created_at) OVER (`
  - 差异：row_diff only_pred=[('142.20',)] only_gold=[('118.00',)]
- `ec-042` [nested] 统计每个一级分类（parent_id 为空）下所有二级子分类商品的在库总数量（只统计直接挂靠在二级分类下的商品，不含一级分类自身直接挂靠的商品），返回分类名称和商品总数两列，按商品总数降序；总数相同时按分类编号升序。
  - status=ok  error=None
  - 生成 SQL：`SELECT c1.name AS category_name, COALESCE(SUM(il.change), 0) AS total_stock FROM categories c1 LEFT JOIN categories c2 ON c2.parent_id = c1.category_id LEFT JOIN products p ON p.category_id = c2.categ`
  - 差异：row_diff only_pred=[('家电', '6781.00'), ('数码', '3658.00'), ('服饰', '3317.00')] only_gold=[('家电', '61.00'), ('数码', '43.00'), ('服饰', '36.00')]

## 特殊题明细（澄清 / 拒绝）

- `ec-044` 期望=clarify 实际=answer ok=False
- `ec-045` 期望=clarify 实际=answer ok=False
- `ec-048` 期望=clarify 实际=answer ok=False
- `ec-047` 期望=clarify 实际=answer ok=False
- `ec-051` 期望=clarify 实际=answer ok=False
- `ec-052` 期望=clarify 实际=answer ok=False
- `ec-049` 期望=clarify 实际=answer ok=False
- `ec-054` 期望=refuse 实际=answer ok=False
- `ec-046` 期望=clarify 实际=answer ok=False
- `ec-053` 期望=clarify 实际=answer ok=False
- `ec-057` 期望=refuse 实际=answer ok=False
- `ec-056` 期望=refuse 实际=answer ok=False
- `ec-055` 期望=refuse 实际=answer ok=False
- `ec-059` 期望=refuse 实际=answer ok=False
- `ec-060` 期望=refuse 实际=answer ok=False
- `ec-058` 期望=refuse 实际=answer ok=False
- `ec-050` 期望=clarify 实际=answer ok=False