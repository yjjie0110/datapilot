# 评测报告 — a1

## 环境
- 模型：`qwen3.8-flash`  temperature=0.0
- Prompt 指纹：`9f64f90d3aa7`
- 数据集：`D:\download\AI\ChatGPT\Work\agent-project-1\datapilot\data\benchmarks\chinook_v0.jsonl`，共 3 题（可判定 3 题）
- 开始时间：2026-10-23 14:47:56

## 汇总

| 指标 | 值 |
| --- | --- |
| EX（无序） | 66.67% |
| EX（有序） | 50.00% |
| Schema 召回率 | %66.67% |
| 平均输入 token | 820 |
| SQL/执行错误率 | 0.00% |
| 特殊题行为正确率 | 0.00% |
| 延迟 P50 / P95 | 8392 / 21086 ms |
| 单题成本 | ¥0.002276 |
| 总成本 | ¥0.0068 |
| 平均 LLM 调用次数 | 1.0 |

## 分题型

| 题型 | 题目数 | 可判定题 | EX |
| --- | --- | --- | --- |
| aggregation | 1 | 1 | 100.0% |
| join | 1 | 1 | 0.0% |
| simple | 1 | 1 | 100.0% |

## 失败清单（前 20 条）

- `ch-003` [join] 每个音乐流派的曲目数量，按数量从高到低排列，数量相同按流派名升序。
  - status=ok  error=None
  - 生成 SQL：`SELECT GenreId, COUNT(*) AS track_count FROM Track GROUP BY GenreId ORDER BY track_count DESC, GenreId ASC`
  - 差异：row_diff only_pred=[('1.00', '1297.00'), ('7.00', '579.00'), ('3.00', '374.00')] only_gold=[('Rock', '1297.00'), ('Latin', '579.00'), ('Metal', '374.00')]

## 特殊题明细（澄清 / 拒绝）
