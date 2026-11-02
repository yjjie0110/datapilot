# 评测报告 — a1

## 环境
- 模型：`qwen3.8-flash`  temperature=0.0
- Prompt 指纹：`c1038e268edf`
- 数据集：`data\benchmarks\sakila_v0.jsonl`，共 20 题（可判定 18 题）
- 开始时间：2026-10-30 21:31:51

## 汇总

| 指标 | 值 |
| --- | --- |
| EX（无序，分母=全部 18 道可判定题） | 55.56% |
| 排序题 EX（有序，分母=15 道 order_sensitive 题） | 53.33% |
| Schema 召回率 | 66.67% |
| 平均输入 token | 1206 |
| SQL/执行错误率 | 0.00% |
| 特殊题行为正确率 | 0.00% |
| 延迟 P50 / P95 | 27601 / 194401 ms |
| 单题成本 | ¥0.006416 |
| 总成本 | ¥0.1283 |
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
| aggregation | 7 | 7 | 71.4% |
| ambiguous | 1 | 0 | - |
| join | 4 | 4 | 25.0% |
| nested | 4 | 4 | 50.0% |
| simple | 3 | 3 | 66.7% |

## 失败清单（前 20 条）

- `sa-001` [simple] 全库时长最长的 15 部电影是哪些？返回电影标题和时长（分钟），按时长从高到低排列。
  - status=ok  error=None
  - 生成 SQL：`SELECT NULL AS title, NULL AS length WHERE 1 = 0 LIMIT 15;`
  - 差异：row_count_diff pred=0 gold=15
- `sa-005` [aggregation] 统计每位客户的租借次数，取租借次数最多的前 30 名，返回名、姓和租借次数三列，按租借次数降序。
  - status=ok  error=None
  - 生成 SQL：`WITH customer_rentals AS (SELECT c.customer_id, c.first_name, c.last_name, COUNT(r.rental_id) AS rental_count, ROW_NUMBER() OVER (ORDER BY COUNT(r.rental_id) DESC, c.customer_id ASC) AS rn FROM custom`
  - 差异：row_diff only_pred=[('ROSEMARY', 'SCHMIDT', '35.00'), ('PRISCILLA', 'LOWE', '35.00')] only_gold=[('HARRY', 'ARCE', '35.00'), ('BOBBY', 'BOUDREAU', '35.00')]
- `sa-012` [aggregation] 统计每位演员出演过的电影数量，取出演电影数量最多的前 45 位，返回名、姓和出演数量三列，按出演数量降序。
  - status=ok  error=None
  - 生成 SQL：`WITH actor_film_count AS (SELECT a.actor_id, a.first_name, a.last_name, COUNT(DISTINCT fa.film_id) AS film_count FROM actor a LEFT JOIN film_actor fa ON a.actor_id = fa.actor_id GROUP BY a.actor_id, a`
  - 差异：row_diff only_pred=[('MARY', 'TANDY', '31.00'), ('WOODY', 'JOLIE', '31.00')] only_gold=[('PENELOPE', 'CRONYN', '31.00'), ('RIVER', 'DEAN', '31.00')]
- `sa-013` [join] How many films have never been rented even once?
  - status=ok  error=None
  - 生成 SQL：`WITH films AS (SELECT DISTINCT film_id FROM film_category), rented_films AS (SELECT DISTINCT inventory_id AS film_id FROM rental) SELECT COUNT(*) AS never_rented_films FROM films f WHERE NOT EXISTS (S`
  - 差异：row_diff only_pred=[('1.00',)] only_gold=[('42.00',)]
- `sa-014` [join] 门店 2 的客户中，租借次数最多的前 30 位是谁？返回名、姓、所在城市和租借次数四列，按租借次数降序。
  - status=ok  error=None
  - 生成 SQL：`WITH rental_counts AS (SELECT c.customer_id, c.first_name, c.last_name, ci.city, COUNT(r.rental_id) AS rental_count FROM customer c LEFT JOIN rental r ON r.customer_id = c.customer_id LEFT JOIN addres`
  - 差异：row_diff only_pred=[('SARA', 'PERRY', 'Atlixco', '33.00')] only_gold=[('GRACE', 'ELLIS', 'Duisburg', '33.00')]
- `sa-015` [join] 出演过动作片（Action 类别）的演员中，出演动作片数量最多的前 5 位是谁？返回名、姓和动作片数量，按数量从高到低排列，数量相同按姓升序、再按名升序。
  - status=ok  error=None
  - 生成 SQL：`WITH action_films AS (SELECT fc.film_id FROM film_category AS fc JOIN category AS c ON fc.category_id = c.category_id WHERE c.name = 'Action'), candidate_actors AS (SELECT NULL AS first_name, NULL AS `
  - 差异：row_count_diff pred=0 gold=5
- `sa-016` [nested] 租金单价高于同评级电影平均租金单价的电影中，租金单价最高的 20 部是哪些？返回电影标题、评级和租金单价三列，按租金单价从高到低排列。
  - status=ok  error=None
  - 生成 SQL：`WITH film_avg AS (SELECT film_id, title, rating, rental_rate, AVG(rental_rate) OVER (PARTITION BY rating) AS avg_rental_rate FROM film), ranked AS (SELECT title, rating, rental_rate, ROW_NUMBER() OVER`
  - 差异：row_diff only_pred=[('ACE GOLDFINGER', 'G', '4.99'), ('AIRPORT POLLOCK', 'R', '4.99'), ('ALADDIN CALENDAR', 'NC-17', '4.99')] only_gold=[('BLINDNESS GUN', 'PG-13', '4.99'), ('DESPERATE TRAINSPOTTING', 'G', '4.99'), ('JINGLE SAGEBRUSH', 'PG-13', '4.99')]
- `sa-003` [nested] 租借次数超过其所属类别平均租借次数的电影，返回电影标题，按标题升序排列，只取前 20 部。
  - status=ok  error=None
  - 生成 SQL：`WITH film_rental_counts AS (SELECT fc.film_id, fc.category_id, COUNT(r.rental_id) AS rental_count FROM film_category AS fc LEFT JOIN rental AS r ON r.inventory_id = fc.film_id GROUP BY fc.film_id, fc.`
  - 差异：row_diff only_pred=[('2.00',), ('6.00',), ('7.00',)] only_gold=[('ACADEMY DINOSAUR',), ('AFFAIR PREJUDICE',), ('AGENT TRUMAN',)]

## 特殊题明细（澄清 / 拒绝）

- `sa-020` 期望=refuse 实际=answer ok=False
- `sa-019` 期望=clarify 实际=answer ok=False