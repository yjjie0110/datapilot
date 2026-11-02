# 评测报告 — a0

## 环境
- 模型：`qwen3.8-flash`  temperature=0.0
- Prompt 指纹：`c1038e268edf`
- 数据集：`data\benchmarks\chinook_v0.jsonl`，共 30 题（可判定 24 题）
- 开始时间：2026-10-30 21:21:08

## 汇总

| 指标 | 值 |
| --- | --- |
| EX（无序，分母=全部 24 道可判定题） | 75.00% |
| 排序题 EX（有序，分母=16 道 order_sensitive 题） | 62.50% |
| Schema 召回率 | N/A |
| 平均输入 token | N/A |
| SQL/执行错误率 | 0.00% |
| 特殊题行为正确率 | 0.00% |
| 延迟 P50 / P95 | 20125 / 48511 ms |
| 单题成本 | ¥0.004093 |
| 总成本 | ¥0.1228 |
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
| nested | 5 | 5 | 80.0% |
| simple | 5 | 5 | 100.0% |

## 失败清单（前 20 条）

- `ch-004` [nested] 哪些专辑的总时长超过 60 分钟？按专辑标题字母序排列。
  - status=ok  error=None
  - 生成 SQL：`SELECT Album.AlbumId, Album.Title, SUM(Track.Milliseconds) / 60000.0 AS total_minutes FROM Album JOIN Track ON Album.AlbumId = Track.AlbumId GROUP BY Album.AlbumId, Album.Title HAVING SUM(Track.Millis`
  - 差异：col_count_diff pred=3 gold=1
- `ch-005` [join] 消费总额最高的 30 位客户，返回他们的名、姓和累计消费金额，按消费金额降序。
  - status=ok  error=None
  - 生成 SQL：`WITH customer_totals AS (SELECT c.CustomerId, c.FirstName, c.LastName, SUM(i.Total) AS total_spent FROM Customer c JOIN Invoice i ON c.CustomerId = i.CustomerId GROUP BY c.CustomerId, c.FirstName, c.L`
  - 差异：row_diff only_pred=[('Leonie', 'Köhler', '37.62'), ('Daan', 'Peeters', '37.62')] only_gold=[('Roberto', 'Almeida', '37.62'), ('Michelle', 'Brooks', '37.62')]
- `ch-002` [aggregation] 每个国家的客户总消费额，取前 20 名，按消费额降序。
  - status=ok  error=None
  - 生成 SQL：`WITH country_spend AS (SELECT c.Country, SUM(i.Total) AS total_spending FROM Customer c JOIN Invoice i ON c.CustomerId = i.CustomerId WHERE c.Country IS NOT NULL GROUP BY c.Country), ranked AS (SELECT`
  - 差异：col_count_diff pred=3 gold=2
- `ch-013` [join] 按累计售出曲目数量（InvoiceLine 的 Quantity 总和）从少到多列出艺术家，取售出最少的 32 位，返回艺术家名和累计售出数量，按售出数量升序。
  - status=ok  error=None
  - 生成 SQL：`WITH artist_sales AS (SELECT a.ArtistId, a.Name AS ArtistName, COALESCE(SUM(il.Quantity), 0) AS total_quantity FROM Artist AS a LEFT JOIN Album AS al ON a.ArtistId = al.ArtistId LEFT JOIN Track AS t O`
  - 差异：row_diff only_pred=[('Milton Nascimento & Bebeto', '0.00'), ('Azymuth', '0.00'), ('João Gilberto', '0.00')] only_gold=[('Academy of St. Martin in the Fields & Sir Neville Marriner', '1.00'), ('Academy of St. Martin in the Fields, John Birch, Sir Neville Marriner & Sylvia McNair', '1.00'), ('Adrian Leaper & Doreen de Feis', '1.00')]
- `ch-011` [aggregation] 按每张专辑包含的曲目数量从多到少列出专辑，取曲目数最多的前 80 张，返回专辑标题和曲目数量，按曲目数量降序。
  - status=ok  error=None
  - 生成 SQL：`WITH album_counts AS (
  SELECT
    a.AlbumId,
    a.Title,
    COUNT(t.TrackId) AS track_count
  FROM Album AS a
  LEFT JOIN Track AS t ON t.AlbumId = a.AlbumId
  GROUP BY a.AlbumId, a.Title
),
ranke`
  - 差异：row_diff only_pred=[('Warner 25 Anos', '14.00')] only_gold=[('Angel Dust', '14.00')]
- `ch-017` [aggregation] 2025 年每个月的发票总额，以及该月相对上月的金额变化（本月总额 − 上月总额，保留 2 位小数；1 月为 NULL），月份按 'YYYY-MM' 格式输出，按月从早到晚排列。
  - status=ok  error=None
  - 生成 SQL：`WITH RECURSIVE months AS (SELECT '2025-01' AS month UNION ALL SELECT strftime('%Y-%m', date(month, '+1 month')) FROM months WHERE month < '2025-12'), monthly AS (SELECT strftime('%Y-%m', InvoiceDate) `
  - 差异：row_count_diff pred=2 gold=12

## 特殊题明细（澄清 / 拒绝）

- `ch-008` 期望=refuse 实际=answer ok=False
- `ch-007` 期望=clarify 实际=answer ok=False
- `ch-029` 期望=clarify 实际=answer ok=False
- `ch-027` 期望=clarify 实际=answer ok=False
- `ch-028` 期望=clarify 实际=answer ok=False
- `ch-030` 期望=refuse 实际=answer ok=False