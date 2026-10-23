# 评测报告 — a1

## 环境
- 模型：`qwen3.8-flash`  temperature=0.0
- Prompt 指纹：`9f64f90d3aa7`
- 数据集：`data\benchmarks\sakila_v0.jsonl`，共 20 题（可判定 18 题）
- 开始时间：2026-10-23 15:13:12

## 汇总

| 指标 | 值 |
| --- | --- |
| EX（无序，分母=全部 18 道可判定题） | 66.67% |
| 排序题 EX（有序，分母=15 道 order_sensitive 题） | 73.33% |
| Schema 召回率 | 61.11% |
| 平均输入 token | 857 |
| SQL/执行错误率 | 0.00% |
| 特殊题行为正确率 | 0.00% |
| 延迟 P50 / P95 | 18714 / 252695 ms |
| 单题成本 | ¥0.006638 |
| 总成本 | ¥0.1328 |
| 平均 LLM 调用次数 | 1.0 |

## 分题型

| 题型 | 题目数 | 可判定题 | EX |
| --- | --- | --- | --- |
| adversarial | 1 | 0 | - |
| aggregation | 5 | 5 | 100.0% |
| ambiguous | 1 | 0 | - |
| join | 5 | 5 | 20.0% |
| nested | 4 | 4 | 50.0% |
| simple | 4 | 4 | 100.0% |

## 失败清单（前 20 条）

- `sa-002` [join] 每个国家客户的支付总额，取前 5 名。金额相同按国家名升序。
  - status=ok  error=None
  - 生成 SQL：`SELECT country.country, 0 AS total_payment FROM customer JOIN address ON customer.address_id = address.address_id JOIN city ON address.city_id = city.city_id JOIN country ON city.country_id = country.`
  - 差异：row_diff only_pred=[('Afghanistan', '0.00'), ('Algeria', '0.00'), ('American Samoa', '0.00')] only_gold=[('India', '6630.27'), ('China', '5802.73'), ('United States', '4110.32')]
- `sa-014` [join] For store 2, which 5 customers made the most rentals? Return first name, last name, their city, and rental count, ordered by count descending, then last name, then first name.
  - status=ok  error=None
  - 生成 SQL：`SELECT c.first_name, c.last_name, a.city_id AS city, COUNT(r.rental_id) AS rental_count FROM rental AS r JOIN inventory AS i ON r.inventory_id = i.inventory_id JOIN customer AS c ON r.customer_id = c.`
  - 差异：row_diff only_pred=[('JORGE', 'OLIVARES', '301.00', '26.00'), ('ELEANOR', 'HUNT', '442.00', '25.00'), ('CLARA', 'SHAW', '340.00', '25.00')] only_gold=[('KARL', 'SEAL', 'Cape Coral', '45.00'), ('TAMMY', 'SANDERS', 'Changhwa', '41.00'), ('WESLEY', 'BULL', 'Ourense (Orense)', '40.00')]
- `sa-013` [join] How many films have never been rented even once?
  - status=ok  error=None
  - 生成 SQL：`SELECT 0 AS films_never_rented;`
  - 差异：row_diff only_pred=[('0.00',)] only_gold=[('42.00',)]
- `sa-017` [nested] 有多少位已停用（非活跃）的客户仍然存在付款记录？
  - status=ok  error=None
  - 生成 SQL：`SELECT COUNT(*) AS inactive_customers_with_payment_records FROM customer WHERE active = '0' AND 1 = 0;`
  - 差异：row_diff only_pred=[('0.00',)] only_gold=[('15.00',)]
- `sa-015` [join] 出演过动作片（Action 类别）的演员中，出演动作片数量最多的前 5 位是谁？返回名、姓和动作片数量，按数量从高到低排列，数量相同按姓升序、再按名升序。
  - status=ok  error=None
  - 生成 SQL：`WITH action_films AS (SELECT fc.film_id FROM film_category AS fc JOIN category AS c ON fc.category_id = c.category_id WHERE c.name = 'Action'), actor_counts AS (SELECT NULL AS first_name, NULL AS last`
  - 差异：row_count_diff pred=0 gold=5
- `sa-003` [nested] 租借次数超过其所属类别平均租借次数的电影，返回电影标题，按标题升序排列，只取前 20 部。
  - status=ok  error=None
  - 生成 SQL：`SELECT NULL AS title WHERE 1 = 0 ORDER BY 1 LIMIT 20`
  - 差异：row_count_diff pred=0 gold=20

## 特殊题明细（澄清 / 拒绝）

- `sa-019` 期望=clarify 实际=answer ok=False
- `sa-020` 期望=refuse 实际=answer ok=False