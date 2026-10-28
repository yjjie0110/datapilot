# 评测报告 — a2

## 环境
- 模型：`qwen3.8-flash`  temperature=0.0
- Prompt 指纹：`084699c0f060`
- 数据集：`data\benchmarks\sakila_v0.jsonl`，共 20 题（可判定 18 题）
- 开始时间：2026-10-28 15:21:29

## 汇总

| 指标 | 值 |
| --- | --- |
| EX（无序，分母=全部 18 道可判定题） | 88.89% |
| 排序题 EX（有序，分母=15 道 order_sensitive 题） | 93.33% |
| Schema 召回率 | 77.78% |
| 平均输入 token | 1041 |
| SQL/执行错误率 | 0.00% |
| 特殊题行为正确率 | 0.00% |
| 延迟 P50 / P95 | 28995 / 81799 ms |
| 单题成本 | ¥0.004968 |
| 总成本 | ¥0.0994 |
| 平均 LLM 调用次数 | 1.1 |
| 首轮正确率 | 83.33% |
| 修复增益 | 5.56% |
| 触发检索扩大次数 | 1 |

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
| join | 5 | 5 | 60.0% |
| nested | 4 | 4 | 100.0% |
| simple | 4 | 4 | 100.0% |

## 失败清单（前 20 条）

- `sa-014` [join] For store 2, which 5 customers made the most rentals? Return first name, last name, their city, and rental count, ordered by count descending, then last name, then first name.
  - status=ok  error=None
  - 生成 SQL：`SELECT c.first_name, c.last_name, a.district AS city, COUNT(r.rental_id) AS rental_count FROM rental r JOIN inventory i ON r.inventory_id = i.inventory_id JOIN customer c ON r.customer_id = c.customer`
  - 差异：row_diff only_pred=[('JORGE', 'OLIVARES', '', '26.00'), ('ELEANOR', 'HUNT', '', '25.00'), ('CLARA', 'SHAW', '', '25.00')] only_gold=[('KARL', 'SEAL', 'Cape Coral', '45.00'), ('TAMMY', 'SANDERS', 'Changhwa', '41.00'), ('WESLEY', 'BULL', 'Ourense (Orense)', '40.00')]
- `sa-013` [join] How many films have never been rented even once?
  - status=ok  error=None
  - 生成 SQL：`WITH films AS (SELECT DISTINCT film_id FROM film_category UNION SELECT DISTINCT film_id FROM film_actor), rented AS (SELECT DISTINCT inventory_id AS film_id FROM rental) SELECT COUNT(*) FROM films WHE`
  - 差异：row_diff only_pred=[('1.00',)] only_gold=[('42.00',)]

## 特殊题明细（澄清 / 拒绝）

- `sa-020` 期望=refuse 实际=answer ok=False
- `sa-019` 期望=clarify 实际=answer ok=False