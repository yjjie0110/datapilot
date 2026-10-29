# 评测报告 — a4

## 环境
- 模型：`qwen3.8-flash`  temperature=0.0
- Prompt 指纹：`a32cc524ca69`
- 数据集：`data\benchmarks\chinook_v0.jsonl`，共 30 题（可判定 24 题）
- 开始时间：2026-10-29 13:02:54

## 汇总

| 指标 | 值 |
| --- | --- |
| EX（无序，分母=全部 24 道可判定题） | 95.83% |
| 排序题 EX（有序，分母=15 道 order_sensitive 题） | 93.33% |
| Schema 召回率 | 95.83% |
| 平均输入 token | 2324 |
| SQL/执行错误率 | 0.00% |
| 特殊题行为正确率 | 83.33% |
| 延迟 P50 / P95 | 20488 / 71628 ms |
| 单题成本 | ¥0.005803 |
| 总成本 | ¥0.1741 |
| 平均 LLM 调用次数 | 2.33 |
| 首轮正确率 | 91.67% |
| 修复增益 | 4.17% |
| 触发检索扩大次数 | 1 |
| gate 误杀 answer 题数 | 0 |
| verify 触发数 | 24 |
| verify 修复成功数 | 0 |
| verify 误杀数 | 0 |

## 行为混淆矩阵
| 期望 \ 实际 | answer | clarify | refuse |
| --- | --- | --- | --- |
| answer | 24 | 0 | 0 |
| clarify | 1 | 3 | 0 |
| refuse | 0 | 0 | 2 |
## 分题型

| 题型 | 题目数 | 可判定题 | EX |
| --- | --- | --- | --- |
| adversarial | 2 | 0 | - |
| aggregation | 5 | 5 | 100.0% |
| ambiguous | 4 | 0 | - |
| join | 7 | 7 | 85.7% |
| nested | 5 | 5 | 100.0% |
| simple | 7 | 7 | 100.0% |

## 失败清单（前 20 条）

- `ch-022` [join] 按艺术家统计累计售出曲目数量（Quantity 总和）及其占全部销量的百分比（保留 1 位小数），取前 5 名，返回艺术家名、销量和百分比，按销量从高到低排列，销量相同按艺术家名升序。
  - status=ok  error=None
  - 生成 SQL：`WITH artist_sales AS (SELECT t.Composer AS artist_name, SUM(il.Quantity) AS sales FROM InvoiceLine il JOIN Track t ON il.TrackId = t.TrackId GROUP BY t.Composer), total AS (SELECT SUM(sales) AS total_`
  - 差异：row_diff only_pred=[('<NULL>', '594.00', '26.50'), ('Steve Harris', '58.00', '2.60'), ('U2', '33.00', '1.50')] only_gold=[('Iron Maiden', '140.00', '6.30'), ('U2', '107.00', '4.80'), ('Metallica', '91.00', '4.10')]

## 特殊题明细（澄清 / 拒绝）

- `ch-008` 期望=refuse 实际=refuse ok=True
- `ch-007` 期望=clarify 实际=clarify ok=True
- `ch-027` 期望=clarify 实际=clarify ok=True
- `ch-028` 期望=clarify 实际=clarify ok=True
- `ch-030` 期望=refuse 实际=refuse ok=True
- `ch-029` 期望=clarify 实际=answer ok=False