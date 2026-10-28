# 评测报告 — a3

## 环境
- 模型：`qwen3.8-flash`  temperature=0.0
- Prompt 指纹：`084699c0f060`
- 数据集：`D:\download\AI\ChatGPT\Work\agent-project-1\datapilot\data\benchmarks\chinook_v0.jsonl`，共 30 题（可判定 24 题）
- 开始时间：2026-10-28 15:06:43

## 汇总

| 指标 | 值 |
| --- | --- |
| EX（无序，分母=全部 24 道可判定题） | 91.67% |
| 排序题 EX（有序，分母=15 道 order_sensitive 题） | 86.67% |
| Schema 召回率 | 95.83% |
| 平均输入 token | 2208 |
| SQL/执行错误率 | 0.00% |
| 特殊题行为正确率 | 83.33% |
| 延迟 P50 / P95 | 15357 / 74478 ms |
| 单题成本 | ¥0.004900 |
| 总成本 | ¥0.1470 |
| 平均 LLM 调用次数 | 2.27 |
| 首轮正确率 | 87.50% |
| 修复增益 | 4.17% |
| 触发检索扩大次数 | 1 |
| gate 误杀 answer 题数 | 1 |
| verify 触发数 | 23 |
| verify 修复成功数 | 0 |
| verify 误杀数 | 0 |

## 行为混淆矩阵
| 期望 \ 实际 | answer | clarify | refuse |
| --- | --- | --- | --- |
| answer | 23 | 1 | 0 |
| clarify | 1 | 3 | 0 |
| refuse | 0 | 0 | 2 |
## 分题型

| 题型 | 题目数 | 可判定题 | EX |
| --- | --- | --- | --- |
| adversarial | 2 | 0 | - |
| aggregation | 5 | 5 | 100.0% |
| ambiguous | 4 | 0 | - |
| join | 7 | 7 | 85.7% |
| nested | 5 | 5 | 80.0% |
| simple | 7 | 7 | 100.0% |

## 失败清单（前 20 条）

- `ch-023` [nested] 找出消费总额高于其所在国家客户平均消费额的客户，返回名、姓和消费总额，按消费总额从高到低排列，金额相同按姓氏升序。
  - status=clarified  error=None
  - 生成 SQL：``
- `ch-022` [join] 按艺术家统计累计售出曲目数量（Quantity 总和）及其占全部销量的百分比（保留 1 位小数），取前 5 名，返回艺术家名、销量和百分比，按销量从高到低排列，销量相同按艺术家名升序。
  - status=ok  error=None
  - 生成 SQL：`WITH artist_sales AS (SELECT t.Composer AS ArtistName, SUM(il.Quantity) AS Sales FROM InvoiceLine AS il JOIN Track AS t ON t.TrackId = il.TrackId WHERE t.Composer IS NOT NULL GROUP BY t.Composer), tot`
  - 差异：row_diff only_pred=[('Steve Harris', '58.00', '2.60'), ('U2', '33.00', '1.50'), ('Billy Corgan', '23.00', '1.00')] only_gold=[('Iron Maiden', '140.00', '6.30'), ('U2', '107.00', '4.80'), ('Metallica', '91.00', '4.10')]

## 特殊题明细（澄清 / 拒绝）

- `ch-007` 期望=clarify 实际=clarify ok=True
- `ch-008` 期望=refuse 实际=refuse ok=True
- `ch-027` 期望=clarify 实际=clarify ok=True
- `ch-028` 期望=clarify 实际=clarify ok=True
- `ch-030` 期望=refuse 实际=refuse ok=True
- `ch-029` 期望=clarify 实际=answer ok=False