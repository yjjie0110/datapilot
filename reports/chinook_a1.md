# 评测报告 — a1

## 环境
- 模型：`qwen3.8-flash`  temperature=0.0
- Prompt 指纹：`a7d099e8ee30`
- 数据集：`data\benchmarks\chinook_v0.jsonl`，共 30 题（可判定 24 题）
- 开始时间：2026-10-29 19:28:05

## 汇总

| 指标 | 值 |
| --- | --- |
| EX（无序，分母=全部 24 道可判定题） | 87.50% |
| 排序题 EX（有序，分母=15 道 order_sensitive 题） | 86.67% |
| Schema 召回率 | 91.67% |
| 平均输入 token | 983 |
| SQL/执行错误率 | 0.00% |
| 特殊题行为正确率 | 0.00% |
| 延迟 P50 / P95 | 9998 / 35325 ms |
| 单题成本 | ¥0.003410 |
| 总成本 | ¥0.1023 |
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
| aggregation | 5 | 5 | 100.0% |
| ambiguous | 4 | 0 | - |
| join | 7 | 7 | 71.4% |
| nested | 5 | 5 | 100.0% |
| simple | 7 | 7 | 85.7% |

## 失败清单（前 20 条）

- `ch-010` [simple] 列出所有姓 Smith 的客户的姓名和邮箱。
  - status=ok  error=None
  - 生成 SQL：`SELECT FirstName || ' ' || LastName AS Name, Email FROM Customer WHERE LastName = 'Smith';`
  - 差异：col_count_diff pred=2 gold=3
- `ch-021` [join] 每位销售支持代理（Sales Support Agent）名下有多少位客户、这些客户的总消费金额是多少？返回姓氏、名字、客户数和总消费金额，按客户数从高到低排列，客户数相同按姓氏升序。
  - status=ok  error=None
  - 生成 SQL：`SELECT e.LastName, e.FirstName, COUNT(c.CustomerId) AS CustomerCount, CAST(NULL AS NUMERIC) AS TotalSpent FROM Employee AS e LEFT JOIN Customer AS c ON c.SupportRepId = e.EmployeeId WHERE LOWER(e.Titl`
  - 差异：row_diff only_pred=[('Peacock', 'Jane', '21.00', '<NULL>'), ('Park', 'Margaret', '20.00', '<NULL>'), ('Johnson', 'Steve', '18.00', '<NULL>')] only_gold=[('Peacock', 'Jane', '21.00', '833.04'), ('Park', 'Margaret', '20.00', '775.40'), ('Johnson', 'Steve', '18.00', '720.16')]
- `ch-022` [join] 按艺术家统计累计售出曲目数量（Quantity 总和）及其占全部销量的百分比（保留 1 位小数），取前 5 名，返回艺术家名、销量和百分比，按销量从高到低排列，销量相同按艺术家名升序。
  - status=ok  error=None
  - 生成 SQL：`WITH total_sales AS (SELECT SUM(Quantity) AS total_quantity FROM InvoiceLine), artist_sales AS (SELECT t.Composer AS artist_name, SUM(il.Quantity) AS sold_quantity FROM InvoiceLine AS il JOIN Track AS`
  - 差异：row_diff only_pred=[('Steve Harris', '58.00', '2.60'), ('U2', '33.00', '1.50'), ('Billy Corgan', '23.00', '1.00')] only_gold=[('Iron Maiden', '140.00', '6.30'), ('U2', '107.00', '4.80'), ('Metallica', '91.00', '4.10')]

## 特殊题明细（澄清 / 拒绝）

- `ch-008` 期望=refuse 实际=answer ok=False
- `ch-007` 期望=clarify 实际=answer ok=False
- `ch-027` 期望=clarify 实际=answer ok=False
- `ch-029` 期望=clarify 实际=answer ok=False
- `ch-030` 期望=refuse 实际=answer ok=False
- `ch-028` 期望=clarify 实际=answer ok=False