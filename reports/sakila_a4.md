# 评测报告 — a4

## 环境
- 模型：`qwen3.8-flash`  temperature=0.0
- Prompt 指纹：`a7d099e8ee30`
- 数据集：`data\benchmarks\sakila_v0.jsonl`，共 20 题（可判定 18 题）
- 开始时间：2026-10-30 12:10:32

## 汇总

| 指标 | 值 |
| --- | --- |
| EX（无序，分母=全部 18 道可判定题） | 72.22% |
| 排序题 EX（有序，分母=15 道 order_sensitive 题） | 66.67% |
| Schema 召回率 | 77.78% |
| 平均输入 token | 3114 |
| SQL/执行错误率 | 0.00% |
| 特殊题行为正确率 | 100.00% |
| 延迟 P50 / P95 | 24772 / 109636 ms |
| 单题成本 | ¥0.007686 |
| 总成本 | ¥0.1537 |
| 平均 LLM 调用次数 | 2.75 |
| 首轮正确率 | 66.67% |
| 修复增益 | 5.56% |
| 触发检索扩大次数 | 2 |
| gate 误杀 answer 题数 | 0 |
| verify 触发数 | 18 |
| verify 修复成功数 | 0 |
| verify 误杀数 | 0 |

## 行为混淆矩阵
| 期望 \ 实际 | answer | clarify | refuse |
| --- | --- | --- | --- |
| answer | 18 | 0 | 0 |
| clarify | 0 | 1 | 0 |
| refuse | 0 | 0 | 1 |
## 分题型

| 题型 | 题目数 | 可判定题 | EX |
| --- | --- | --- | --- |
| adversarial | 1 | 0 | - |
| aggregation | 7 | 7 | 71.4% |
| ambiguous | 1 | 0 | - |
| join | 4 | 4 | 75.0% |
| nested | 4 | 4 | 75.0% |
| simple | 3 | 3 | 66.7% |

## 失败清单（前 20 条）

- `sa-005` [aggregation] 统计每位客户的租借次数，取租借次数最多的前 30 名，返回名、姓和租借次数三列，按租借次数降序。
  - status=ok  error=None
  - 生成 SQL：`SELECT c.first_name, c.last_name, COUNT(r.rental_id) AS rental_count FROM customer c JOIN rental r ON c.customer_id = r.customer_id GROUP BY c.customer_id, c.first_name, c.last_name ORDER BY rental_co`
  - 差异：row_diff only_pred=[('ROSEMARY', 'SCHMIDT', '35.00'), ('PRISCILLA', 'LOWE', '35.00')] only_gold=[('HARRY', 'ARCE', '35.00'), ('BOBBY', 'BOUDREAU', '35.00')]
- `sa-001` [simple] 全库时长最长的 15 部电影是哪些？返回电影标题和时长（分钟），按时长从高到低排列。
  - status=ok  error=None
  - 生成 SQL：`SELECT title, length FROM film ORDER BY length DESC LIMIT 15`
  - 差异：row_diff only_pred=[('MOONWALKER FOOL', '184.00')] only_gold=[('SORORITY QUEEN', '184.00')]
- `sa-012` [aggregation] 统计每位演员出演过的电影数量，取出演电影数量最多的前 45 位，返回名、姓和出演数量三列，按出演数量降序。
  - status=ok  error=None
  - 生成 SQL：`SELECT a.first_name, a.last_name, COUNT(DISTINCT fa.film_id) AS film_count FROM actor AS a LEFT JOIN film_actor AS fa ON a.actor_id = fa.actor_id GROUP BY a.actor_id, a.first_name, a.last_name ORDER B`
  - 差异：row_diff only_pred=[('MARY', 'TANDY', '31.00'), ('WOODY', 'JOLIE', '31.00')] only_gold=[('PENELOPE', 'CRONYN', '31.00'), ('RIVER', 'DEAN', '31.00')]
- `sa-014` [join] 门店 2 的客户中，租借次数最多的前 30 位是谁？返回名、姓、所在城市和租借次数四列，按租借次数降序。
  - status=ok  error=None
  - 生成 SQL：`WITH rental_counts AS (SELECT c.customer_id, COUNT(r.rental_id) AS rental_count FROM customer AS c LEFT JOIN rental AS r ON r.customer_id = c.customer_id WHERE c.store_id = 2 GROUP BY c.customer_id) S`
  - 差异：row_diff only_pred=[('SARA', 'PERRY', 'Atlixco', '33.00')] only_gold=[('GRACE', 'ELLIS', 'Duisburg', '33.00')]
- `sa-016` [nested] 租金单价高于同评级电影平均租金单价的电影中，租金单价最高的 20 部是哪些？返回电影标题、评级和租金单价三列，按租金单价从高到低排列。
  - status=ok  error=None
  - 生成 SQL：`WITH rating_avg AS (SELECT rating, AVG(rental_rate) AS avg_rental_rate FROM film GROUP BY rating) SELECT f.title, f.rating, f.rental_rate FROM film AS f JOIN rating_avg AS r ON f.rating = r.rating WHE`
  - 差异：row_diff only_pred=[('ACE GOLDFINGER', 'G', '4.99'), ('AIRPORT POLLOCK', 'R', '4.99'), ('ALADDIN CALENDAR', 'NC-17', '4.99')] only_gold=[('BLINDNESS GUN', 'PG-13', '4.99'), ('DESPERATE TRAINSPOTTING', 'G', '4.99'), ('JINGLE SAGEBRUSH', 'PG-13', '4.99')]

## 特殊题明细（澄清 / 拒绝）

- `sa-019` 期望=clarify 实际=clarify ok=True
- `sa-020` 期望=refuse 实际=refuse ok=True