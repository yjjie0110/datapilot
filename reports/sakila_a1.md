# 评测报告 — a1

## 环境
- 模型：`qwen3.8-flash`  temperature=0.0
- Prompt 指纹：`a7d099e8ee30`
- 数据集：`data\benchmarks\sakila_v0.jsonl`，共 20 题（可判定 18 题）
- 开始时间：2026-10-30 12:00:57

## 汇总

| 指标 | 值 |
| --- | --- |
| EX（无序，分母=全部 18 道可判定题） | 61.11% |
| 排序题 EX（有序，分母=15 道 order_sensitive 题） | 60.00% |
| Schema 召回率 | 66.67% |
| 平均输入 token | 1077 |
| SQL/执行错误率 | 0.00% |
| 特殊题行为正确率 | 0.00% |
| 延迟 P50 / P95 | 16378 / 93003 ms |
| 单题成本 | ¥0.006151 |
| 总成本 | ¥0.1230 |
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
| nested | 4 | 4 | 75.0% |
| simple | 3 | 3 | 66.7% |

## 失败清单（前 20 条）

- `sa-005` [aggregation] 统计每位客户的租借次数，取租借次数最多的前 30 名，返回名、姓和租借次数三列，按租借次数降序。
  - status=ok  error=None
  - 生成 SQL：`SELECT c.first_name, c.last_name, COUNT(r.rental_id) AS rental_count FROM customer AS c LEFT JOIN rental AS r ON c.customer_id = r.customer_id GROUP BY c.customer_id, c.first_name, c.last_name ORDER B`
  - 差异：row_diff only_pred=[('ROSEMARY', 'SCHMIDT', '35.00'), ('PRISCILLA', 'LOWE', '35.00')] only_gold=[('HARRY', 'ARCE', '35.00'), ('BOBBY', 'BOUDREAU', '35.00')]
- `sa-001` [simple] 全库时长最长的 15 部电影是哪些？返回电影标题和时长（分钟），按时长从高到低排列。
  - status=ok  error=None
  - 生成 SQL：`SELECT title AS title, length AS length FROM film ORDER BY length DESC LIMIT 15;`
  - 差异：row_diff only_pred=[('MOONWALKER FOOL', '184.00')] only_gold=[('SORORITY QUEEN', '184.00')]
- `sa-012` [aggregation] 统计每位演员出演过的电影数量，取出演电影数量最多的前 45 位，返回名、姓和出演数量三列，按出演数量降序。
  - status=ok  error=None
  - 生成 SQL：`SELECT a.first_name, a.last_name, COUNT(fa.film_id) AS film_count FROM actor AS a JOIN film_actor AS fa ON a.actor_id = fa.actor_id GROUP BY a.actor_id, a.first_name, a.last_name ORDER BY film_count D`
  - 差异：row_diff only_pred=[('MARY', 'TANDY', '31.00'), ('WOODY', 'JOLIE', '31.00')] only_gold=[('PENELOPE', 'CRONYN', '31.00'), ('RIVER', 'DEAN', '31.00')]
- `sa-014` [join] 门店 2 的客户中，租借次数最多的前 30 位是谁？返回名、姓、所在城市和租借次数四列，按租借次数降序。
  - status=ok  error=None
  - 生成 SQL：`SELECT c.first_name AS "名", c.last_name AS "姓", ci.city AS "所在城市", COUNT(r.rental_id) AS "租借次数" FROM customer c JOIN rental r ON r.customer_id = c.customer_id JOIN address a ON a.address_id = c.addres`
  - 差异：row_diff only_pred=[('SARA', 'PERRY', 'Atlixco', '33.00')] only_gold=[('GRACE', 'ELLIS', 'Duisburg', '33.00')]
- `sa-013` [join] How many films have never been rented even once?
  - status=ok  error=None
  - 生成 SQL：`SELECT COUNT(DISTINCT fc.film_id) AS films_never_rented FROM film_category AS fc WHERE NOT EXISTS (SELECT 1 FROM rental AS r WHERE r.inventory_id = fc.film_id);`
  - 差异：row_diff only_pred=[('1.00',)] only_gold=[('42.00',)]
- `sa-016` [nested] 租金单价高于同评级电影平均租金单价的电影中，租金单价最高的 20 部是哪些？返回电影标题、评级和租金单价三列，按租金单价从高到低排列。
  - status=ok  error=None
  - 生成 SQL：`SELECT NULL AS title, NULL AS rating, NULL AS rental_rate FROM category WHERE 1 = 0 LIMIT 20`
  - 差异：row_count_diff pred=0 gold=20
- `sa-015` [join] 出演过动作片（Action 类别）的演员中，出演动作片数量最多的前 5 位是谁？返回名、姓和动作片数量，按数量从高到低排列，数量相同按姓升序、再按名升序。
  - status=ok  error=None
  - 生成 SQL：`SELECT NULL AS first_name, NULL AS last_name, NULL AS action_film_count FROM film_category AS fc JOIN category AS c ON fc.category_id = c.category_id WHERE c.name = 'Action' AND 1 = 0 ORDER BY action_`
  - 差异：row_count_diff pred=0 gold=5

## 特殊题明细（澄清 / 拒绝）

- `sa-019` 期望=clarify 实际=answer ok=False
- `sa-020` 期望=refuse 实际=answer ok=False