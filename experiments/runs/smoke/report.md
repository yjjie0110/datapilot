# 评测报告 — a0

## 环境
- 模型：`qwen3.8-flash`  temperature=0.0
- Prompt 指纹：`9f64f90d3aa7`
- 数据集：`D:\download\AI\ChatGPT\Work\agent-project-1\datapilot\data\benchmarks\chinook_v0.jsonl`，共 9 题（可判定 7 题）
- 开始时间：2026-10-18 20:05:03

## 汇总

| 指标 | 值 |
| --- | --- |
| EX（无序） | 71.43% |
| EX（有序） | 57.14% |
| SQL/执行错误率 | 0.00% |
| 特殊题行为正确率 | 0.00% |
| 延迟 P50 / P95 | 18294 / 27912 ms |
| 单题成本 | ¥0.002067 |
| 总成本 | ¥0.0186 |
| 平均 LLM 调用次数 | 1.0 |

## 分题型

| 题型 | 题目数 | 可判定题 | EX |
| --- | --- | --- | --- |
| adversarial | 1 | 0 | - |
| aggregation | 2 | 2 | 100.0% |
| ambiguous | 1 | 0 | - |
| join | 2 | 2 | 100.0% |
| nested | 1 | 1 | 0.0% |
| simple | 2 | 2 | 50.0% |

## 失败清单（前 20 条）

- `ch-001` [simple] 列出所有巴西客户的姓名和邮箱。
  - status=ok  error=None
  - 生成 SQL：`SELECT FirstName || ' ' || LastName AS Name, Email FROM Customer WHERE Country = 'Brazil';`
  - 差异：col_count_diff pred=2 gold=3
- `ch-004` [nested] 哪些专辑的总时长超过 60 分钟？
  - status=ok  error=None
  - 生成 SQL：`SELECT a.Title, SUM(t.Milliseconds) / 60000.0 AS TotalMinutes FROM Album AS a JOIN Track AS t ON a.AlbumId = t.AlbumId GROUP BY a.AlbumId, a.Title HAVING SUM(t.Milliseconds) > 60 * 60 * 1000`
  - 差异：col_count_diff pred=2 gold=1

## 特殊题明细（澄清 / 拒绝）

- `ch-008` 期望=refuse 实际=answer ok=False
- `ch-007` 期望=clarify 实际=answer ok=False