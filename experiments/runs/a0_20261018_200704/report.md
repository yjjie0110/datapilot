# 评测报告 — a0

## 环境
- 模型：`qwen3.8-flash`  temperature=0.0
- Prompt 指纹：`9f64f90d3aa7`
- 数据集：`D:\download\AI\ChatGPT\Work\agent-project-1\datapilot\data\benchmarks\chinook_v0.jsonl`，共 30 题（可判定 24 题）
- 开始时间：2026-10-18 20:07:04

## 汇总

| 指标 | 值 |
| --- | --- |
| EX（无序） | 95.83% |
| EX（有序） | 87.50% |
| SQL/执行错误率 | 0.00% |
| 特殊题行为正确率 | 0.00% |
| 延迟 P50 / P95 | 8107 / 22403 ms |
| 单题成本 | ¥0.002016 |
| 总成本 | ¥0.0605 |
| 平均 LLM 调用次数 | 1.0 |

## 分题型

| 题型 | 题目数 | 可判定题 | EX |
| --- | --- | --- | --- |
| adversarial | 2 | 0 | - |
| aggregation | 5 | 5 | 100.0% |
| ambiguous | 4 | 0 | - |
| join | 7 | 7 | 100.0% |
| nested | 5 | 5 | 100.0% |
| simple | 7 | 7 | 85.7% |

## 失败清单（前 20 条）

- `ch-001` [simple] 列出所有巴西客户的姓名和邮箱。
  - status=ok  error=None
  - 生成 SQL：`SELECT FirstName || ' ' || LastName AS Name, Email FROM Customer WHERE Country = 'Brazil';`
  - 差异：col_count_diff pred=2 gold=3

## 特殊题明细（澄清 / 拒绝）

- `ch-008` 期望=refuse 实际=answer ok=False
- `ch-007` 期望=clarify 实际=answer ok=False
- `ch-027` 期望=clarify 实际=answer ok=False
- `ch-028` 期望=clarify 实际=answer ok=False
- `ch-029` 期望=clarify 实际=answer ok=False
- `ch-030` 期望=refuse 实际=answer ok=False