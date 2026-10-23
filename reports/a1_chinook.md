# 评测报告 — a1

## 环境
- 模型：`qwen3.8-flash`  temperature=0.0
- Prompt 指纹：`9f64f90d3aa7`
- 数据集：`D:\download\AI\ChatGPT\Work\agent-project-1\datapilot\data\benchmarks\chinook_v0.jsonl`，共 30 题（可判定 24 题）
- 开始时间：2026-10-23 15:13:10

## 汇总

| 指标 | 值 |
| --- | --- |
| EX（无序，分母=全部 24 道可判定题） | 79.17% |
| 排序题 EX（有序，分母=3 道 order_sensitive 题） | 66.67% |
| Schema 召回率 | 79.17% |
| 平均输入 token | 801 |
| SQL/执行错误率 | 0.00% |
| 特殊题行为正确率 | 0.00% |
| 延迟 P50 / P95 | 10849 / 60866 ms |
| 单题成本 | ¥0.003965 |
| 总成本 | ¥0.1190 |
| 平均 LLM 调用次数 | 1.0 |

## 分题型

| 题型 | 题目数 | 可判定题 | EX |
| --- | --- | --- | --- |
| adversarial | 2 | 0 | - |
| aggregation | 5 | 5 | 100.0% |
| ambiguous | 4 | 0 | - |
| join | 7 | 7 | 42.9% |
| nested | 5 | 5 | 80.0% |
| simple | 7 | 7 | 100.0% |

## 失败清单（前 20 条）

- `ch-003` [join] 每个音乐流派的曲目数量，按数量从高到低排列，数量相同按流派名升序。
  - status=ok  error=None
  - 生成 SQL：`SELECT GenreId AS GenreName, COUNT(TrackId) AS TrackCount FROM Track GROUP BY GenreId ORDER BY TrackCount DESC, GenreName ASC;`
  - 差异：row_diff only_pred=[('1.00', '1297.00'), ('7.00', '579.00'), ('3.00', '374.00')] only_gold=[('Rock', '1297.00'), ('Latin', '579.00'), ('Metal', '374.00')]
- `ch-022` [join] 按艺术家统计累计售出曲目数量（Quantity 总和）及其占全部销量的百分比（保留 1 位小数），取前 5 名，返回艺术家名、销量和百分比，按销量从高到低排列，销量相同按艺术家名升序。
  - status=ok  error=None
  - 生成 SQL：`WITH total_sales AS (SELECT COALESCE(SUM(Quantity), 0) AS total_qty FROM InvoiceLine), artist_sales AS (SELECT t.Composer AS ArtistName, SUM(il.Quantity) AS Sales FROM InvoiceLine il JOIN Track t ON i`
  - 差异：row_diff only_pred=[('Steve Harris', '58.00', '2.60'), ('U2', '33.00', '1.50'), ('Billy Corgan', '23.00', '1.00')] only_gold=[('Iron Maiden', '140.00', '6.30'), ('U2', '107.00', '4.80'), ('Metallica', '91.00', '4.10')]
- `ch-021` [join] 每位销售支持代理（Sales Support Agent）名下有多少位客户、这些客户的总消费金额是多少？返回姓氏、名字、客户数和总消费金额，按客户数从高到低排列，客户数相同按姓氏升序。
  - status=ok  error=None
  - 生成 SQL：`SELECT e.LastName, e.FirstName, COUNT(c.CustomerId) AS CustomerCount, CAST(NULL AS NUMERIC) AS TotalConsumption FROM Employee AS e LEFT JOIN Customer AS c ON c.SupportRepId = e.EmployeeId WHERE e.Titl`
  - 差异：row_diff only_pred=[('Peacock', 'Jane', '21.00', '<NULL>'), ('Park', 'Margaret', '20.00', '<NULL>'), ('Johnson', 'Steve', '18.00', '<NULL>')] only_gold=[('Peacock', 'Jane', '21.00', '833.04'), ('Park', 'Margaret', '20.00', '775.40'), ('Johnson', 'Steve', '18.00', '720.16')]
- `ch-024` [nested] 从未出现在任何发票中的曲目有多少首？
  - status=ok  error=None
  - 生成 SQL：`SELECT COUNT(*) FROM Track`
  - 差异：row_diff only_pred=[('3503.00',)] only_gold=[('1519.00',)]
- `ch-020` [join] 有多少首曲目在 2024 年和 2025 年都出现在发票中（即两年都被售出过）？
  - status=ok  error=None
  - 生成 SQL：`SELECT 0;`
  - 差异：row_diff only_pred=[('0.00',)] only_gold=[('9.00',)]

## 特殊题明细（澄清 / 拒绝）

- `ch-008` 期望=refuse 实际=answer ok=False
- `ch-007` 期望=clarify 实际=answer ok=False
- `ch-027` 期望=clarify 实际=answer ok=False
- `ch-029` 期望=clarify 实际=answer ok=False
- `ch-028` 期望=clarify 实际=answer ok=False
- `ch-030` 期望=refuse 实际=answer ok=False