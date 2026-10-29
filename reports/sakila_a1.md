# 评测报告 — a1

## 环境
- 模型：`qwen3.8-flash`  temperature=0.0
- Prompt 指纹：`a32cc524ca69`
- 数据集：`data\benchmarks\sakila_v0.jsonl`，共 20 题（可判定 18 题）
- 开始时间：2026-10-29 12:39:35

## 汇总

| 指标 | 值 |
| --- | --- |
| EX（无序，分母=全部 18 道可判定题） | 77.78% |
| 排序题 EX（有序，分母=15 道 order_sensitive 题） | 80.00% |
| Schema 召回率 | 72.22% |
| 平均输入 token | 1066 |
| SQL/执行错误率 | 0.00% |
| 特殊题行为正确率 | 0.00% |
| 延迟 P50 / P95 | 19955 / 72009 ms |
| 单题成本 | ¥0.005000 |
| 总成本 | ¥0.1000 |
| 平均 LLM 调用次数 | 1.0 |
| 首轮正确率 | N/A |
| 修复增益 | N/A |
| 触发检索扩大次数 | 0 |

## 行为混淆矩阵
| 期望 \ 实际 | answer |
| --- | --- |
| answer | 18 |
| clarify | 1 |
| refuse | 1 |
## 分题型

| 题型 | 题目数 | 可判定题 | EX |
| --- | --- | --- | --- |
| adversarial | 1 | 0 | - |
| aggregation | 5 | 5 | 100.0% |
| ambiguous | 1 | 0 | - |
| join | 5 | 5 | 40.0% |
| nested | 4 | 4 | 75.0% |
| simple | 4 | 4 | 100.0% |

## 失败清单（前 20 条）

- `sa-003` [nested] 租借次数超过其所属类别平均租借次数的电影，返回电影标题，按标题升序排列，只取前 20 部。
  - status=ok  error=None
  - 生成 SQL：`SELECT NULL AS title FROM film_category WHERE 1 = 0 ORDER BY title LIMIT 20`
  - 差异：row_count_diff pred=0 gold=20
- `sa-014` [join] For store 2, which 5 customers made the most rentals? Return first name, last name, their city, and rental count, ordered by count descending, then last name, then first name.
  - status=ok  error=None
  - 生成 SQL：`SELECT c.first_name, c.last_name, a.city_id AS city, COUNT(r.rental_id) AS rental_count FROM rental r JOIN inventory i ON r.inventory_id = i.inventory_id JOIN customer c ON r.customer_id = c.customer_`
  - 差异：row_diff only_pred=[('JORGE', 'OLIVARES', '301.00', '26.00'), ('ELEANOR', 'HUNT', '442.00', '25.00'), ('CLARA', 'SHAW', '340.00', '25.00')] only_gold=[('KARL', 'SEAL', 'Cape Coral', '45.00'), ('TAMMY', 'SANDERS', 'Changhwa', '41.00'), ('WESLEY', 'BULL', 'Ourense (Orense)', '40.00')]
- `sa-015` [join] 出演过动作片（Action 类别）的演员中，出演动作片数量最多的前 5 位是谁？返回名、姓和动作片数量，按数量从高到低排列，数量相同按姓升序、再按名升序。
  - status=ok  error=None
  - 生成 SQL：`SELECT NULL AS first_name, NULL AS last_name, 0 AS action_film_count FROM category JOIN film_category ON category.category_id = film_category.category_id WHERE category.name = 'Action' AND 1 = 0 ORDER`
  - 差异：row_count_diff pred=0 gold=5
- `sa-013` [join] How many films have never been rented even once?
  - status=ok  error=None
  - 生成 SQL：`WITH all_films AS (SELECT DISTINCT film_id FROM film_category UNION SELECT DISTINCT film_id FROM film_actor), rented_films AS (SELECT DISTINCT inventory_id AS film_id FROM rental) SELECT COUNT(*) AS n`
  - 差异：row_diff only_pred=[('1.00',)] only_gold=[('42.00',)]

## 特殊题明细（澄清 / 拒绝）

- `sa-020` 期望=refuse 实际=answer ok=False
- `sa-019` 期望=clarify 实际=answer ok=False