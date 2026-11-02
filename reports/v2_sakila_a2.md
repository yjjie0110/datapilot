# 评测报告 — a2

## 环境
- 模型：`qwen3.8-flash`  temperature=0.0
- Prompt 指纹：`c1038e268edf`
- 数据集：`data\benchmarks\sakila_v0.jsonl`，共 20 题（可判定 18 题）
- 开始时间：2026-10-30 21:49:41

## 汇总

| 指标 | 值 |
| --- | --- |
| EX（无序，分母=全部 18 道可判定题） | 66.67% |
| 排序题 EX（有序，分母=15 道 order_sensitive 题） | 60.00% |
| Schema 召回率 | 77.78% |
| 平均输入 token | 1862 |
| SQL/执行错误率 | 0.00% |
| 特殊题行为正确率 | 0.00% |
| 延迟 P50 / P95 | 48535 / 212252 ms |
| 单题成本 | ¥0.013767 |
| 总成本 | ¥0.2753 |
| 平均 LLM 调用次数 | 2.2 |
| 首轮正确率 | 66.67% |
| 修复增益 | 0.00% |
| 触发检索扩大次数 | 2 |

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
| join | 4 | 4 | 50.0% |
| nested | 4 | 4 | 75.0% |
| simple | 3 | 3 | 66.7% |

## 失败清单（前 20 条）

- `sa-001` [simple] 全库时长最长的 15 部电影是哪些？返回电影标题和时长（分钟），按时长从高到低排列。
  - status=ok  error=None
  - 生成 SQL：`WITH ranked_films AS (SELECT title, length, ROW_NUMBER() OVER (ORDER BY length DESC, film_id ASC) AS rn FROM film) SELECT title, length FROM ranked_films WHERE rn <= 15 ORDER BY rn ASC;`
  - 差异：row_diff only_pred=[('MOONWALKER FOOL', '184.00')] only_gold=[('SORORITY QUEEN', '184.00')]
- `sa-005` [aggregation] 统计每位客户的租借次数，取租借次数最多的前 30 名，返回名、姓和租借次数三列，按租借次数降序。
  - status=ok  error=None
  - 生成 SQL：`WITH rental_counts AS (SELECT c.customer_id, c.first_name, c.last_name, COUNT(r.rental_id) AS rental_count FROM customer AS c LEFT JOIN rental AS r ON c.customer_id = r.customer_id GROUP BY c.customer`
  - 差异：row_diff only_pred=[('ROSEMARY', 'SCHMIDT', '35.00'), ('PRISCILLA', 'LOWE', '35.00')] only_gold=[('HARRY', 'ARCE', '35.00'), ('BOBBY', 'BOUDREAU', '35.00')]
- `sa-012` [aggregation] 统计每位演员出演过的电影数量，取出演电影数量最多的前 45 位，返回名、姓和出演数量三列，按出演数量降序。
  - status=ok  error=None
  - 生成 SQL：`WITH actor_film_count AS (
  SELECT
    a.actor_id,
    a.first_name,
    a.last_name,
    COUNT(fa.film_id) AS film_count
  FROM actor a
  LEFT JOIN film_actor fa ON a.actor_id = fa.actor_id
  GROUP `
  - 差异：row_diff only_pred=[('MARY', 'TANDY', '31.00'), ('WOODY', 'JOLIE', '31.00')] only_gold=[('PENELOPE', 'CRONYN', '31.00'), ('RIVER', 'DEAN', '31.00')]
- `sa-014` [join] 门店 2 的客户中，租借次数最多的前 30 位是谁？返回名、姓、所在城市和租借次数四列，按租借次数降序。
  - status=ok  error=None
  - 生成 SQL：`WITH rental_counts AS (SELECT c.customer_id, c.first_name, c.last_name, ci.city, COUNT(r.rental_id) AS rental_count FROM customer AS c JOIN address AS a ON c.address_id = a.address_id JOIN city AS ci `
  - 差异：row_diff only_pred=[('SARA', 'PERRY', 'Atlixco', '33.00')] only_gold=[('GRACE', 'ELLIS', 'Duisburg', '33.00')]
- `sa-015` [join] 出演过动作片（Action 类别）的演员中，出演动作片数量最多的前 5 位是谁？返回名、姓和动作片数量，按数量从高到低排列，数量相同按姓升序、再按名升序。
  - status=ok  error=None
  - 生成 SQL：`WITH action_films AS (SELECT fc.film_id FROM film_category AS fc JOIN category AS c ON fc.category_id = c.category_id WHERE c.name = 'Action'), counts AS (SELECT film_id AS actor_id, COUNT(*) AS actio`
  - 差异：row_diff only_pred=[('19.00', '19.00', '1.00'), ('21.00', '21.00', '1.00'), ('29.00', '29.00', '1.00')] only_gold=[('NATALIE', 'HOPKINS', '6.00'), ('KIRSTEN', 'AKROYD', '5.00'), ('JON', 'CHASE', '5.00')]
- `sa-016` [nested] 租金单价高于同评级电影平均租金单价的电影中，租金单价最高的 20 部是哪些？返回电影标题、评级和租金单价三列，按租金单价从高到低排列。
  - status=ok  error=None
  - 生成 SQL：`WITH avg_rating AS (SELECT rating, AVG(rental_rate) AS avg_rental_rate FROM film GROUP BY rating), ranked AS (SELECT f.title, f.rating, f.rental_rate, ROW_NUMBER() OVER (ORDER BY f.rental_rate DESC, f`
  - 差异：row_diff only_pred=[('ACE GOLDFINGER', 'G', '4.99'), ('AIRPORT POLLOCK', 'R', '4.99'), ('ALADDIN CALENDAR', 'NC-17', '4.99')] only_gold=[('BLINDNESS GUN', 'PG-13', '4.99'), ('DESPERATE TRAINSPOTTING', 'G', '4.99'), ('JINGLE SAGEBRUSH', 'PG-13', '4.99')]

## 特殊题明细（澄清 / 拒绝）

- `sa-019` 期望=clarify 实际=answer ok=False
- `sa-020` 期望=refuse 实际=answer ok=False