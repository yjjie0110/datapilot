# 评测报告 — a3

## 环境
- 模型：`qwen3.8-flash`  temperature=0.0
- Prompt 指纹：`084699c0f060`
- 数据集：`data\benchmarks\sakila_v0.jsonl`，共 20 题（可判定 18 题）
- 开始时间：2026-10-27 20:55:44

## 汇总

| 指标 | 值 |
| --- | --- |
| EX（无序，分母=全部 18 道可判定题） | 88.89% |
| 排序题 EX（有序，分母=15 道 order_sensitive 题） | 93.33% |
| Schema 召回率 | 77.78% |
| 平均输入 token | 2775 |
| SQL/执行错误率 | 0.00% |
| 特殊题行为正确率 | 50.00% |
| 延迟 P50 / P95 | 35682 / 133044 ms |
| 单题成本 | ¥0.008921 |
| 总成本 | ¥0.1784 |
| 平均 LLM 调用次数 | 2.7 |
| 首轮正确率 | 0.8333 |
| 修复增益 | 0.0556 |
| 出发检索扩大次数 | 1 |
## 行为混淆矩阵
| 期望 \ 实际 | answer | clarify |
| --- | --- | --- |
| answer | 18 | 0 |
| clarify | 0 | 1 |
| refuse | 1 | 0 |
## 分题型

| 题型 | 题目数 | 可判定题 | EX |
| --- | --- | --- | --- |
| adversarial | 1 | 0 | - |
| aggregation | 5 | 5 | 100.0% |
| ambiguous | 1 | 0 | - |
| join | 5 | 5 | 80.0% |
| nested | 4 | 4 | 75.0% |
| simple | 4 | 4 | 100.0% |

## 失败清单（前 20 条）

- `sa-017` [nested] 有多少位已停用（非活跃）的客户仍然存在付款记录？
  - status=ok  error=None
  - 生成 SQL：`SELECT COUNT(DISTINCT p.customer_id) FROM payment AS p JOIN customer AS c ON p.customer_id = c.customer_id WHERE c.active = 'N'`
  - 差异：row_diff only_pred=[('0.00',)] only_gold=[('15.00',)]
- `sa-014` [join] For store 2, which 5 customers made the most rentals? Return first name, last name, their city, and rental count, ordered by count descending, then last name, then first name.
  - status=ok  error=None
  - 生成 SQL：`SELECT c.first_name, c.last_name, ci.city, COUNT(r.rental_id) AS rental_count FROM rental AS r JOIN inventory AS i ON r.inventory_id = i.inventory_id JOIN customer AS c ON r.customer_id = c.customer_i`
  - 差异：row_diff only_pred=[('JORGE', 'OLIVARES', 'Lhokseumawe', '26.00'), ('ELEANOR', 'HUNT', 'Saint-Denis', '25.00'), ('CLARA', 'SHAW', 'Molodetno', '25.00')] only_gold=[('KARL', 'SEAL', 'Cape Coral', '45.00'), ('TAMMY', 'SANDERS', 'Changhwa', '41.00'), ('WESLEY', 'BULL', 'Ourense (Orense)', '40.00')]

## 特殊题明细（澄清 / 拒绝）

- `sa-019` 期望=clarify 实际=clarify ok=True
- `sa-020` 期望=refuse 实际=answer ok=False