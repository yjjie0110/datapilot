# 评测报告 — a2

## 环境
- 模型：`qwen3.8-flash`  temperature=0.0
- Prompt 指纹：`9f64f90d3aa7`
- 数据集：`D:\download\AI\ChatGPT\Work\agent-project-1\datapilot\data\benchmarks\chinook_v0.jsonl`，共 30 题（可判定 24 题）
- 开始时间：2026-10-27 12:40:10

## 汇总

| 指标 | 值 |
| --- | --- |
| EX（无序，分母=全部 24 道可判定题） | 87.50% |
| 排序题 EX（有序，分母=15 道 order_sensitive 题） | 80.00% |
| Schema 召回率 | 91.30% |
| 平均输入 token | 925 |
| SQL/执行错误率 | 4.17% |
| 特殊题行为正确率 | 0.00% |
| 延迟 P50 / P95 | 8691 / 41699 ms |
| 单题成本 | ¥0.002944 |
| 总成本 | ¥0.0883 |
| 平均 LLM 调用次数 | 1.03 |
| 首轮正确率 | 0.913 |
| 修复增益 | -0.038 |
| 出发检索扩大次数 | 1 |
## 分题型

| 题型 | 题目数 | 可判定题 | EX |
| --- | --- | --- | --- |
| adversarial | 2 | 0 | - |
| aggregation | 5 | 5 | 100.0% |
| ambiguous | 4 | 0 | - |
| join | 7 | 7 | 57.1% |
| nested | 5 | 5 | 100.0% |
| simple | 7 | 7 | 100.0% |

## 失败清单（前 20 条）

- `ch-003` [join] 每个音乐流派的曲目数量，按数量从高到低排列，数量相同按流派名升序。
  - status=error  error=OperationalError: database is locked
  - 生成 SQL：``
- `ch-022` [join] 按艺术家统计累计售出曲目数量（Quantity 总和）及其占全部销量的百分比（保留 1 位小数），取前 5 名，返回艺术家名、销量和百分比，按销量从高到低排列，销量相同按艺术家名升序。
  - status=ok  error=None
  - 生成 SQL：`SELECT t.Composer AS Artist, SUM(il.Quantity) AS Sales, ROUND(SUM(il.Quantity) * 100.0 / (SELECT SUM(Quantity) FROM InvoiceLine), 1) AS Percentage FROM InvoiceLine il JOIN Track t ON il.TrackId = t.Tr`
  - 差异：row_diff only_pred=[('Steve Harris', '58.00', '2.60'), ('U2', '33.00', '1.50'), ('Billy Corgan', '23.00', '1.00')] only_gold=[('Iron Maiden', '140.00', '6.30'), ('U2', '107.00', '4.80'), ('Metallica', '91.00', '4.10')]
- `ch-021` [join] 每位销售支持代理（Sales Support Agent）名下有多少位客户、这些客户的总消费金额是多少？返回姓氏、名字、客户数和总消费金额，按客户数从高到低排列，客户数相同按姓氏升序。
  - status=ok  error=None
  - 生成 SQL：`SELECT e.LastName, e.FirstName, COUNT(c.CustomerId) AS CustomerCount, 0 AS TotalConsumption FROM Employee AS e LEFT JOIN Customer AS c ON c.SupportRepId = e.EmployeeId WHERE e.Title = 'Sales Support A`
  - 差异：row_diff only_pred=[('Peacock', 'Jane', '21.00', '0.00'), ('Park', 'Margaret', '20.00', '0.00'), ('Johnson', 'Steve', '18.00', '0.00')] only_gold=[('Peacock', 'Jane', '21.00', '833.04'), ('Park', 'Margaret', '20.00', '775.40'), ('Johnson', 'Steve', '18.00', '720.16')]

## 特殊题明细（澄清 / 拒绝）

- `ch-008` 期望=refuse 实际=answer ok=False
- `ch-007` 期望=clarify 实际=answer ok=False
- `ch-028` 期望=clarify 实际=answer ok=False
- `ch-029` 期望=clarify 实际=answer ok=False
- `ch-030` 期望=refuse 实际=answer ok=False
- `ch-027` 期望=clarify 实际=answer ok=False