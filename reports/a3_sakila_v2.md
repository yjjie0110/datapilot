# 评测报告 — a3

## 环境
- 模型：`qwen3.8-flash`  temperature=0.0
- Prompt 指纹：`084699c0f060`
- 数据集：`data\benchmarks\sakila_v0.jsonl`，共 20 题（可判定 18 题）
- 开始时间：2026-10-27 22:54:16

## 汇总

| 指标 | 值 |
| --- | --- |
| EX（无序，分母=全部 18 道可判定题） | 72.22% |
| 排序题 EX（有序，分母=15 道 order_sensitive 题） | 73.33% |
| Schema 召回率 | 72.22% |
| 平均输入 token | 2608 |
| SQL/执行错误率 | 5.56% |
| 特殊题行为正确率 | 100.00% |
| 延迟 P50 / P95 | 31324 / 1289872 ms |
| 单题成本 | ¥0.010300 |
| 总成本 | ¥0.2060 |
| 平均 LLM 调用次数 | 2.6 |
| 首轮正确率 | 72.22% |
| 修复增益 | 0.00% |
| 触发检索扩大次数 | 0 |
| gate 误杀 answer 题数 | 1 |
| verify 触发数 | 16 |
| verify 修复成功数 | 0 |
| verify 误杀数 | 0 |

## 行为混淆矩阵
| 期望 \ 实际 | answer | clarify | refuse |
| --- | --- | --- | --- |
| answer | 17 | 1 | 0 |
| clarify | 0 | 1 | 0 |
| refuse | 0 | 0 | 1 |
## 分题型

| 题型 | 题目数 | 可判定题 | EX |
| --- | --- | --- | --- |
| adversarial | 1 | 0 | - |
| aggregation | 5 | 5 | 100.0% |
| ambiguous | 1 | 0 | - |
| join | 5 | 5 | 40.0% |
| nested | 4 | 4 | 75.0% |
| simple | 4 | 4 | 75.0% |

## 失败清单（前 20 条）

- `sa-003` [nested] 租借次数超过其所属类别平均租借次数的电影，返回电影标题，按标题升序排列，只取前 20 部。
  - status=sql_error  error=None
  - 生成 SQL：``
- `sa-004` [simple] List the first name, last name, and email of all active customers whose last name starts with 'S'. Order by last name, then first name.
  - status=ok  error=None
  - 生成 SQL：`SELECT first_name, last_name, email FROM customer WHERE active = 'Y' AND last_name LIKE 'S%' ORDER BY last_name, first_name`
  - 差异：row_count_diff pred=0 gold=54
- `sa-013` [join] How many films have never been rented even once?
  - status=ok  error=None
  - 生成 SQL：`WITH known_films AS (SELECT film_id FROM film_actor UNION SELECT film_id FROM film_category) SELECT COUNT(*) FROM known_films kf WHERE NOT EXISTS (SELECT 1 FROM rental r WHERE r.inventory_id = kf.film`
  - 差异：row_diff only_pred=[('1.00',)] only_gold=[('42.00',)]
- `sa-014` [join] For store 2, which 5 customers made the most rentals? Return first name, last name, their city, and rental count, ordered by count descending, then last name, then first name.
  - status=ok  error=None
  - 生成 SQL：`SELECT c.first_name, c.last_name, ci.city AS city, COUNT(r.rental_id) AS rental_count FROM rental r JOIN inventory i ON r.inventory_id = i.inventory_id JOIN customer c ON r.customer_id = c.customer_id`
  - 差异：row_diff only_pred=[('JORGE', 'OLIVARES', 'Lhokseumawe', '26.00'), ('ELEANOR', 'HUNT', 'Saint-Denis', '25.00'), ('CLARA', 'SHAW', 'Molodetno', '25.00')] only_gold=[('KARL', 'SEAL', 'Cape Coral', '45.00'), ('TAMMY', 'SANDERS', 'Changhwa', '41.00'), ('WESLEY', 'BULL', 'Ourense (Orense)', '40.00')]
- `sa-015` [join] 出演过动作片（Action 类别）的演员中，出演动作片数量最多的前 5 位是谁？返回名、姓和动作片数量，按数量从高到低排列，数量相同按姓升序、再按名升序。
  - status=ok  error=None
  - 生成 SQL：`SELECT fc.film_id AS first_name, fc.film_id AS last_name, COUNT(*) AS action_count FROM film_category AS fc JOIN category AS c ON fc.category_id = c.category_id WHERE c.name = 'Action' GROUP BY fc.fil`
  - 差异：row_diff only_pred=[('19.00', '19.00', '1.00'), ('21.00', '21.00', '1.00'), ('29.00', '29.00', '1.00')] only_gold=[('NATALIE', 'HOPKINS', '6.00'), ('KIRSTEN', 'AKROYD', '5.00'), ('JON', 'CHASE', '5.00')]

## 特殊题明细（澄清 / 拒绝）

- `sa-019` 期望=clarify 实际=clarify ok=True
- `sa-020` 期望=refuse 实际=refuse ok=True