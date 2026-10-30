# 评测报告 — a0

## 环境
- 模型：`qwen3.8-flash`  temperature=0.0
- Prompt 指纹：`a7d099e8ee30`
- 数据集：`data\benchmarks\chinook_v0.jsonl`，共 30 题（可判定 24 题）
- 开始时间：2026-10-30 10:34:09

## 汇总

| 指标 | 值 |
| --- | --- |
| EX（无序，分母=全部 24 道可判定题） | 79.17% |
| 排序题 EX（有序，分母=16 道 order_sensitive 题） | 68.75% |
| Schema 召回率 | N/A |
| 平均输入 token | N/A |
| SQL/执行错误率 | 0.00% |
| 特殊题行为正确率 | 0.00% |
| 延迟 P50 / P95 | 12353 / 71065 ms |
| 单题成本 | ¥0.003736 |
| 总成本 | ¥0.1121 |
| 平均 LLM 调用次数 | 1.0 |
| 首轮正确率 | N/A |
| 修复增益 | N/A |
| 触发检索扩大次数 | 0 |

## 行为混淆矩阵
| 期望 \ 实际 | answer |
| --- | --- |
| answer | 24 |
| clarify | 4 |
| refuse | 2 |
## 分题型

| 题型 | 题目数 | 可判定题 | EX |
| --- | --- | --- | --- |
| adversarial | 2 | 0 | - |
| aggregation | 6 | 6 | 50.0% |
| ambiguous | 4 | 0 | - |
| join | 8 | 8 | 75.0% |
| nested | 5 | 5 | 100.0% |
| simple | 5 | 5 | 100.0% |

## 失败清单（前 20 条）

- `ch-002` [aggregation] 每个国家的客户总消费额，取前 20 名，按消费额降序。
  - status=ok  error=None
  - 生成 SQL：`SELECT c.Country, SUM(i.Total) AS total_spent FROM Customer AS c LEFT JOIN Invoice AS i ON c.CustomerId = i.CustomerId GROUP BY c.Country ORDER BY total_spent DESC LIMIT 20`
  - 差异：row_diff only_pred=[('Spain', '37.62'), ('Poland', '37.62'), ('Italy', '37.62')] only_gold=[('Argentina', '37.62'), ('Australia', '37.62'), ('Belgium', '37.62')]
- `ch-005` [join] 消费总额最高的 30 位客户，返回他们的名、姓和累计消费金额，按消费金额降序。
  - status=ok  error=None
  - 生成 SQL：`SELECT c.FirstName, c.LastName, SUM(i.Total) AS total_spent FROM Customer c JOIN Invoice i ON c.CustomerId = i.CustomerId GROUP BY c.CustomerId, c.FirstName, c.LastName ORDER BY total_spent DESC LIMIT`
  - 差异：row_diff only_pred=[('Leonie', 'Köhler', '37.62'), ('Daan', 'Peeters', '37.62')] only_gold=[('Roberto', 'Almeida', '37.62'), ('Michelle', 'Brooks', '37.62')]
- `ch-011` [aggregation] 按每张专辑包含的曲目数量从多到少列出专辑，取曲目数最多的前 80 张，返回专辑标题和曲目数量，按曲目数量降序。
  - status=ok  error=None
  - 生成 SQL：`SELECT a.Title, COUNT(t.TrackId) AS TrackCount FROM Track t JOIN Album a ON t.AlbumId = a.AlbumId GROUP BY a.AlbumId, a.Title ORDER BY TrackCount DESC LIMIT 80;`
  - 差异：row_diff only_pred=[('Warner 25 Anos', '14.00')] only_gold=[('Angel Dust', '14.00')]
- `ch-013` [join] 按累计售出曲目数量（InvoiceLine 的 Quantity 总和）从少到多列出艺术家，取售出最少的 32 位，返回艺术家名和累计售出数量，按售出数量升序。
  - status=ok  error=None
  - 生成 SQL：`WITH artist_sales AS (
  SELECT a.Name, SUM(il.Quantity) AS total_sold
  FROM Artist a
  JOIN Album al ON al.ArtistId = a.ArtistId
  JOIN Track t ON t.AlbumId = al.AlbumId
  JOIN InvoiceLine il ON il.`
  - 差异：row_diff only_pred=[('Aquaman', '2.00')] only_gold=[('Academy of St. Martin in the Fields, Sir Neville Marriner & Thurston Dart', '2.00')]
- `ch-016` [aggregation] 按消费总额从高到低给所有客户排名（金额相同给相同名次），返回排名、名、姓和消费总额，取前 5 名，名次相同按姓氏升序。
  - status=ok  error=None
  - 生成 SQL：`WITH customer_spend AS (SELECT c.CustomerId, c.FirstName, c.LastName, COALESCE(SUM(i.Total), 0) AS total_spend FROM Customer AS c LEFT JOIN Invoice AS i ON c.CustomerId = i.CustomerId GROUP BY c.Custo`
  - 差异：row_count_diff pred=8 gold=5

## 特殊题明细（澄清 / 拒绝）

- `ch-008` 期望=refuse 实际=answer ok=False
- `ch-007` 期望=clarify 实际=answer ok=False
- `ch-028` 期望=clarify 实际=answer ok=False
- `ch-029` 期望=clarify 实际=answer ok=False
- `ch-027` 期望=clarify 实际=answer ok=False
- `ch-030` 期望=refuse 实际=answer ok=False