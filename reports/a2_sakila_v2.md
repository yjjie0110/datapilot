# 评测报告 — a2

## 环境
- 模型：`qwen3.8-flash`  temperature=0.0
- Prompt 指纹：`9f64f90d3aa7`
- 数据集：`data\benchmarks\sakila_v0.jsonl`，共 20 题（可判定 18 题）
- 开始时间：2026-10-27 12:42:17

## 汇总

| 指标 | 值 |
| --- | --- |
| EX（无序，分母=全部 18 道可判定题） | 72.22% |
| 排序题 EX（有序，分母=15 道 order_sensitive 题） | 73.33% |
| Schema 召回率 | 80.00% |
| 平均输入 token | 1034 |
| SQL/执行错误率 | 16.67% |
| 特殊题行为正确率 | 0.00% |
| 延迟 P50 / P95 | 15507 / 111203 ms |
| 单题成本 | ¥0.004441 |
| 总成本 | ¥0.0888 |
| 平均 LLM 调用次数 | 0.95 |
| 首轮正确率 | 0.8 |
| 修复增益 | -0.0778 |
| 出发检索扩大次数 | 1 |
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

- `sa-004` [simple] List the first name, last name, and email of all active customers whose last name starts with 'S'. Order by last name, then first name.
  - status=error  error=OperationalError: attempt to write a readonly database
  - 生成 SQL：``
- `sa-002` [join] 每个国家客户的支付总额，取前 5 名。金额相同按国家名升序。
  - status=error  error=OperationalError: attempt to write a readonly database
  - 生成 SQL：``
- `sa-003` [nested] 租借次数超过其所属类别平均租借次数的电影，返回电影标题，按标题升序排列，只取前 20 部。
  - status=error  error=OperationalError: attempt to write a readonly database
  - 生成 SQL：``
- `sa-013` [join] How many films have never been rented even once?
  - status=ok  error=None
  - 生成 SQL：`SELECT COUNT(DISTINCT fc.film_id) FROM film_category AS fc WHERE NOT EXISTS (SELECT 1 FROM rental AS r WHERE r.inventory_id = fc.film_id);`
  - 差异：row_diff only_pred=[('1.00',)] only_gold=[('42.00',)]
- `sa-014` [join] For store 2, which 5 customers made the most rentals? Return first name, last name, their city, and rental count, ordered by count descending, then last name, then first name.
  - status=ok  error=None
  - 生成 SQL：`SELECT c.first_name, c.last_name, a.district AS city, COUNT(r.rental_id) AS rental_count FROM customer AS c JOIN address AS a ON c.address_id = a.address_id LEFT JOIN rental AS r ON r.customer_id = c.`
  - 差异：row_diff only_pred=[('KARL', 'SEAL', '', '45.00'), ('TAMMY', 'SANDERS', '', '41.00'), ('WESLEY', 'BULL', '', '40.00')] only_gold=[('KARL', 'SEAL', 'Cape Coral', '45.00'), ('TAMMY', 'SANDERS', 'Changhwa', '41.00'), ('WESLEY', 'BULL', 'Ourense (Orense)', '40.00')]

## 特殊题明细（澄清 / 拒绝）

- `sa-019` 期望=clarify 实际=answer ok=False
- `sa-020` 期望=refuse 实际=answer ok=False