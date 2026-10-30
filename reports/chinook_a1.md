# 评测报告 — a1

## 环境
- 模型：`qwen3.8-flash`  temperature=0.0
- Prompt 指纹：`a7d099e8ee30`
- 数据集：`data\benchmarks\chinook_v0.jsonl`，共 30 题（可判定 24 题）
- 开始时间：2026-10-30 10:40:14

## 汇总

| 指标 | 值 |
| --- | --- |
| EX（无序，分母=全部 24 道可判定题） | 75.00% |
| 排序题 EX（有序，分母=16 道 order_sensitive 题） | 62.50% |
| Schema 召回率 | 87.50% |
| 平均输入 token | 970 |
| SQL/执行错误率 | 0.00% |
| 特殊题行为正确率 | 0.00% |
| 延迟 P50 / P95 | 16320 / 56067 ms |
| 单题成本 | ¥0.003906 |
| 总成本 | ¥0.1172 |
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
| aggregation | 6 | 6 | 66.7% |
| ambiguous | 4 | 0 | - |
| join | 8 | 8 | 50.0% |
| nested | 5 | 5 | 100.0% |
| simple | 5 | 5 | 100.0% |

## 失败清单（前 20 条）

- `ch-002` [aggregation] 每个国家的客户总消费额，取前 20 名，按消费额降序。
  - status=ok  error=None
  - 生成 SQL：`SELECT c.Country, SUM(i.Total) AS total_spent FROM Customer AS c JOIN Invoice AS i ON c.CustomerId = i.CustomerId GROUP BY c.Country ORDER BY total_spent DESC LIMIT 20;`
  - 差异：row_diff only_pred=[('Spain', '37.62'), ('Poland', '37.62'), ('Italy', '37.62')] only_gold=[('Argentina', '37.62'), ('Australia', '37.62'), ('Belgium', '37.62')]
- `ch-005` [join] 消费总额最高的 30 位客户，返回他们的名、姓和累计消费金额，按消费金额降序。
  - status=ok  error=None
  - 生成 SQL：`SELECT c.FirstName, c.LastName, SUM(i.Total) AS TotalSpent FROM Customer c JOIN Invoice i ON c.CustomerId = i.CustomerId GROUP BY c.CustomerId, c.FirstName, c.LastName ORDER BY TotalSpent DESC LIMIT 3`
  - 差异：row_diff only_pred=[('Leonie', 'Köhler', '37.62'), ('Daan', 'Peeters', '37.62')] only_gold=[('Roberto', 'Almeida', '37.62'), ('Michelle', 'Brooks', '37.62')]
- `ch-011` [aggregation] 按每张专辑包含的曲目数量从多到少列出专辑，取曲目数最多的前 80 张，返回专辑标题和曲目数量，按曲目数量降序。
  - status=ok  error=None
  - 生成 SQL：`SELECT a.Title, COUNT(t.TrackId) AS track_count FROM Album AS a JOIN Track AS t ON a.AlbumId = t.AlbumId GROUP BY a.AlbumId, a.Title ORDER BY track_count DESC LIMIT 80;`
  - 差异：row_diff only_pred=[('Warner 25 Anos', '14.00')] only_gold=[('Angel Dust', '14.00')]
- `ch-013` [join] 按累计售出曲目数量（InvoiceLine 的 Quantity 总和）从少到多列出艺术家，取售出最少的 32 位，返回艺术家名和累计售出数量，按售出数量升序。
  - status=ok  error=None
  - 生成 SQL：`SELECT t.Composer AS artist_name, SUM(il.Quantity) AS sold_quantity FROM InvoiceLine AS il JOIN Track AS t ON il.TrackId = t.TrackId WHERE t.Composer IS NOT NULL GROUP BY t.Composer ORDER BY sold_quan`
  - 差异：row_diff only_pred=[('A.Bouchard/J.Bouchard/S.Pearlman', '1.00'), ('A.Isbell/A.Jones/O.Redding', '1.00'), ('Acyi Marques/Arlindo Bruz/Braço, Beto Sem/Zeca Pagodinho', '1.00')] only_gold=[('Academy of St. Martin in the Fields & Sir Neville Marriner', '1.00'), ('Academy of St. Martin in the Fields, John Birch, Sir Neville Marriner & Sylvia McNair', '1.00'), ('Adrian Leaper & Doreen de Feis', '1.00')]
- `ch-021` [join] 每位销售支持代理（Sales Support Agent）名下有多少位客户、这些客户的总消费金额是多少？返回姓氏、名字、客户数和总消费金额，按客户数从高到低排列，客户数相同按姓氏升序。
  - status=ok  error=None
  - 生成 SQL：`SELECT e.LastName, e.FirstName, COUNT(c.CustomerId) AS customer_count, NULL AS total_spent FROM Employee e LEFT JOIN Customer c ON c.SupportRepId = e.EmployeeId WHERE e.Title = 'Sales Support Agent' G`
  - 差异：row_diff only_pred=[('Peacock', 'Jane', '21.00', '<NULL>'), ('Park', 'Margaret', '20.00', '<NULL>'), ('Johnson', 'Steve', '18.00', '<NULL>')] only_gold=[('Peacock', 'Jane', '21.00', '833.04'), ('Park', 'Margaret', '20.00', '775.40'), ('Johnson', 'Steve', '18.00', '720.16')]
- `ch-022` [join] 按艺术家统计累计售出曲目数量（Quantity 总和）及其占全部销量的百分比（保留 1 位小数），取前 5 名，返回艺术家名、销量和百分比，按销量从高到低排列，销量相同按艺术家名升序。
  - status=ok  error=None
  - 生成 SQL：`WITH artist_sales AS (SELECT t.Composer AS artist_name, SUM(il.Quantity) AS sales FROM InvoiceLine AS il JOIN Track AS t ON il.TrackId = t.TrackId WHERE t.Composer IS NOT NULL AND t.Composer <> '' GRO`
  - 差异：row_diff only_pred=[('Steve Harris', '58.00', '2.60'), ('U2', '33.00', '1.50'), ('Billy Corgan', '23.00', '1.00')] only_gold=[('Iron Maiden', '140.00', '6.30'), ('U2', '107.00', '4.80'), ('Metallica', '91.00', '4.10')]

## 特殊题明细（澄清 / 拒绝）

- `ch-008` 期望=refuse 实际=answer ok=False
- `ch-007` 期望=clarify 实际=answer ok=False
- `ch-029` 期望=clarify 实际=answer ok=False
- `ch-027` 期望=clarify 实际=answer ok=False
- `ch-030` 期望=refuse 实际=answer ok=False
- `ch-028` 期望=clarify 实际=answer ok=False