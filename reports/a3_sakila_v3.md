# 评测报告 — a3

## 环境
- 模型：`qwen3.8-flash`  temperature=0.0
- Prompt 指纹：`084699c0f060`
- 数据集：`data\benchmarks\sakila_v0.jsonl`，共 20 题（可判定 18 题）
- 开始时间：2026-10-27 23:43:25

## 汇总

| 指标 | 值 |
| --- | --- |
| EX（无序，分母=全部 18 道可判定题） | 83.33% |
| 排序题 EX（有序，分母=15 道 order_sensitive 题） | 86.67% |
| Schema 召回率 | 77.78% |
| 平均输入 token | 2602 |
| SQL/执行错误率 | 0.00% |
| 特殊题行为正确率 | 100.00% |
| 延迟 P50 / P95 | 29050 / 92733 ms |
| 单题成本 | ¥0.006674 |
| 总成本 | ¥0.1335 |
| 平均 LLM 调用次数 | 2.4 |
| 首轮正确率 | 83.33% |
| 修复增益 | 0.00% |
| 触发检索扩大次数 | 1 |
| gate 误杀 answer 题数 | 1 |
| verify 触发数 | 17 |
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
| join | 5 | 5 | 60.0% |
| nested | 4 | 4 | 75.0% |
| simple | 4 | 4 | 100.0% |

## 失败清单（前 20 条）

- `sa-003` [nested] 租借次数超过其所属类别平均租借次数的电影，返回电影标题，按标题升序排列，只取前 20 部。
  - status=clarified  error=None
  - 生成 SQL：``
- `sa-013` [join] How many films have never been rented even once?
  - status=ok  error=None
  - 生成 SQL：`SELECT COUNT(DISTINCT fc.film_id) FROM film_category AS fc WHERE NOT EXISTS (SELECT 1 FROM rental AS r WHERE r.inventory_id = fc.film_id);`
  - 差异：row_diff only_pred=[('1.00',)] only_gold=[('42.00',)]
- `sa-014` [join] For store 2, which 5 customers made the most rentals? Return first name, last name, their city, and rental count, ordered by count descending, then last name, then first name.
  - status=ok  error=None
  - 生成 SQL：`SELECT c.first_name, c.last_name, ci.city, COUNT(r.rental_id) AS rental_count FROM customer c JOIN rental r ON r.customer_id = c.customer_id JOIN inventory i ON i.inventory_id = r.inventory_id JOIN ad`
  - 差异：row_diff only_pred=[('JORGE', 'OLIVARES', 'Lhokseumawe', '26.00'), ('ELEANOR', 'HUNT', 'Saint-Denis', '25.00'), ('CLARA', 'SHAW', 'Molodetno', '25.00')] only_gold=[('KARL', 'SEAL', 'Cape Coral', '45.00'), ('TAMMY', 'SANDERS', 'Changhwa', '41.00'), ('WESLEY', 'BULL', 'Ourense (Orense)', '40.00')]

## 特殊题明细（澄清 / 拒绝）

- `sa-019` 期望=clarify 实际=clarify ok=True
- `sa-020` 期望=refuse 实际=refuse ok=True