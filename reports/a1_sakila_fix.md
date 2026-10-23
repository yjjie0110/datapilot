# 评测报告 — a1

## 环境
- 模型：`qwen3.8-flash`  temperature=0.0
- Prompt 指纹：`9f64f90d3aa7`
- 数据集：`data\benchmarks\sakila_v0.jsonl`，共 20 题（可判定 18 题）
- 开始时间：2026-10-23 15:49:05

## 汇总

| 指标 | 值 |
| --- | --- |
| EX（无序，分母=全部 18 道可判定题） | 83.33% |
| 排序题 EX（有序，分母=15 道 order_sensitive 题） | 86.67% |
| Schema 召回率 | 72.22% |
| 平均输入 token | 979 |
| SQL/执行错误率 | 0.00% |
| 特殊题行为正确率 | 0.00% |
| 延迟 P50 / P95 | 30045 / 124020 ms |
| 单题成本 | ¥0.005555 |
| 总成本 | ¥0.1111 |
| 平均 LLM 调用次数 | 1.0 |

## 分题型

| 题型 | 题目数 | 可判定题 | EX |
| --- | --- | --- | --- |
| adversarial | 1 | 0 | - |
| aggregation | 5 | 5 | 100.0% |
| ambiguous | 1 | 0 | - |
| join | 5 | 5 | 40.0% |
| nested | 4 | 4 | 100.0% |
| simple | 4 | 4 | 100.0% |

## 失败清单（前 20 条）

- `sa-014` [join] For store 2, which 5 customers made the most rentals? Return first name, last name, their city, and rental count, ordered by count descending, then last name, then first name.
  - status=ok  error=None
  - 生成 SQL：`SELECT c.first_name, c.last_name, ci.city, COUNT(r.rental_id) AS rental_count FROM rental AS r JOIN inventory AS i ON r.inventory_id = i.inventory_id JOIN customer AS c ON r.customer_id = c.customer_i`
  - 差异：row_diff only_pred=[('JORGE', 'OLIVARES', 'Lhokseumawe', '26.00'), ('ELEANOR', 'HUNT', 'Saint-Denis', '25.00'), ('CLARA', 'SHAW', 'Molodetno', '25.00')] only_gold=[('KARL', 'SEAL', 'Cape Coral', '45.00'), ('TAMMY', 'SANDERS', 'Changhwa', '41.00'), ('WESLEY', 'BULL', 'Ourense (Orense)', '40.00')]
- `sa-015` [join] 出演过动作片（Action 类别）的演员中，出演动作片数量最多的前 5 位是谁？返回名、姓和动作片数量，按数量从高到低排列，数量相同按姓升序、再按名升序。
  - status=ok  error=None
  - 生成 SQL：`WITH action_films AS (SELECT fc.film_id, COUNT(*) AS action_film_count FROM film_category AS fc JOIN category AS c ON c.category_id = fc.category_id WHERE c.name = 'Action' GROUP BY fc.film_id) SELECT`
  - 差异：row_diff only_pred=[('<NULL>', '<NULL>', '1.00'), ('<NULL>', '<NULL>', '1.00'), ('<NULL>', '<NULL>', '1.00')] only_gold=[('NATALIE', 'HOPKINS', '6.00'), ('KIRSTEN', 'AKROYD', '5.00'), ('JON', 'CHASE', '5.00')]
- `sa-013` [join] How many films have never been rented even once?
  - status=ok  error=None
  - 生成 SQL：`SELECT COUNT(*) AS never_rented_films FROM (SELECT DISTINCT fc.film_id FROM film_category AS fc WHERE NOT EXISTS (SELECT 1 FROM rental AS r WHERE r.inventory_id = fc.film_id)) AS never_rented;`
  - 差异：row_diff only_pred=[('1.00',)] only_gold=[('42.00',)]

## 特殊题明细（澄清 / 拒绝）

- `sa-020` 期望=refuse 实际=answer ok=False
- `sa-019` 期望=clarify 实际=answer ok=False