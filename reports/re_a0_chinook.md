# 评测报告 — a0

## 环境
- 模型：`qwen3.8-flash`  temperature=0.0
- Prompt 指纹：`084699c0f060`
- 数据集：`D:\download\AI\ChatGPT\Work\agent-project-1\datapilot\data\benchmarks\chinook_v0.jsonl`，共 30 题（可判定 24 题）
- 开始时间：2026-10-28 14:53:13

## 汇总

| 指标 | 值 |
| --- | --- |
| EX（无序，分母=全部 24 道可判定题） | 100.00% |
| 排序题 EX（有序，分母=15 道 order_sensitive 题） | 100.00% |
| Schema 召回率 | N/A |
| 平均输入 token | N/A |
| SQL/执行错误率 | 0.00% |
| 特殊题行为正确率 | 0.00% |
| 延迟 P50 / P95 | 10571 / 38658 ms |
| 单题成本 | ¥0.003056 |
| 总成本 | ¥0.0917 |
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
| join | 7 | 7 | 100.0% |
| nested | 5 | 5 | 100.0% |
| simple | 7 | 7 | 100.0% |

## 失败清单（前 20 条）

（无）

## 特殊题明细（澄清 / 拒绝）

- `ch-008` 期望=refuse 实际=answer ok=False
- `ch-007` 期望=clarify 实际=answer ok=False
- `ch-027` 期望=clarify 实际=answer ok=False
- `ch-029` 期望=clarify 实际=answer ok=False
- `ch-028` 期望=clarify 实际=answer ok=False
- `ch-030` 期望=refuse 实际=answer ok=False