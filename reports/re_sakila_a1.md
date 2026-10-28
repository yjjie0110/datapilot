# 评测报告 — a1

## 环境
- 模型：`qwen3.8-flash`  temperature=0.0
- Prompt 指纹：`084699c0f060`
- 数据集：`data\benchmarks\sakila_v0.jsonl`，共 20 题（可判定 18 题）
- 开始时间：2026-10-28 15:18:16

## 汇总

| 指标 | 值 |
| --- | --- |
| EX（无序，分母=全部 18 道可判定题） | 83.33% |
| 排序题 EX（有序，分母=15 道 order_sensitive 题） | 80.00% |
| Schema 召回率 | 72.22% |
| 平均输入 token | 979 |
| SQL/执行错误率 | 0.00% |
| 特殊题行为正确率 | 0.00% |
| 延迟 P50 / P95 | 13711 / 118104 ms |
| 单题成本 | ¥0.004798 |
| 总成本 | ¥0.0960 |
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
| join | 5 | 5 | 60.0% |
| nested | 4 | 4 | 75.0% |
| simple | 4 | 4 | 100.0% |

## 失败清单（前 20 条）

- `sa-003` [nested] 租借次数超过其所属类别平均租借次数的电影，返回电影标题，按标题升序排列，只取前 20 部。
  - status=ok  error=None
  - 生成 SQL：`SELECT NULL AS title FROM film_category WHERE 1 = 0 ORDER BY title LIMIT 20`
  - 差异：row_count_diff pred=0 gold=20
- `sa-015` [join] 出演过动作片（Action 类别）的演员中，出演动作片数量最多的前 5 位是谁？返回名、姓和动作片数量，按数量从高到低排列，数量相同按姓升序、再按名升序。
  - status=ok  error=None
  - 生成 SQL：`SELECT NULL AS first_name, NULL AS last_name, 0 AS action_count FROM category WHERE 1 = 0 ORDER BY action_count DESC, last_name ASC, first_name ASC LIMIT 5;`
  - 差异：row_count_diff pred=0 gold=5
- `sa-014` [join] For store 2, which 5 customers made the most rentals? Return first name, last name, their city, and rental count, ordered by count descending, then last name, then first name.
  - status=ok  error=None
  - 生成 SQL：`SELECT c.first_name, c.last_name, ci.city, COUNT(r.rental_id) AS rental_count FROM rental AS r JOIN inventory AS i ON r.inventory_id = i.inventory_id JOIN customer AS c ON r.customer_id = c.customer_i`
  - 差异：row_diff only_pred=[('JORGE', 'OLIVARES', 'Lhokseumawe', '26.00'), ('ELEANOR', 'HUNT', 'Saint-Denis', '25.00'), ('CLARA', 'SHAW', 'Molodetno', '25.00')] only_gold=[('KARL', 'SEAL', 'Cape Coral', '45.00'), ('TAMMY', 'SANDERS', 'Changhwa', '41.00'), ('WESLEY', 'BULL', 'Ourense (Orense)', '40.00')]

## 特殊题明细（澄清 / 拒绝）

- `sa-019` 期望=clarify 实际=answer ok=False
- `sa-020` 期望=refuse 实际=answer ok=False