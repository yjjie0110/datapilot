# 评测报告 — a4

## 环境
- 模型：`qwen3.8-flash`  temperature=0.0
- Prompt 指纹：`a32cc524ca69`
- 数据集：`data\benchmarks\ecommerce_v0.jsonl`，共 6 题（可判定 6 题）
- 开始时间：2026-10-29 11:40:35

## 汇总

| 指标 | 值 |
| --- | --- |
| EX（无序，分母=全部 6 道可判定题） | 66.67% |
| 排序题 EX（有序，分母=6 道 order_sensitive 题） | 66.67% |
| Schema 召回率 | 100.00% |
| 平均输入 token | N/A |
| SQL/执行错误率 | 0.00% |
| 特殊题行为正确率 | 0.00% |
| 延迟 P50 / P95 | 1593 / 1699 ms |
| 单题成本 | ¥0.000000 |
| 总成本 | ¥0.0000 |
| 平均 LLM 调用次数 | 2.33 |
| 首轮正确率 | 66.67% |
| 修复增益 | 0.00% |
| 触发检索扩大次数 | 1 |
| gate 误杀 answer 题数 | 1 |
| verify 触发数 | 4 |
| verify 修复成功数 | 0 |
| verify 误杀数 | 0 |

## 行为混淆矩阵
| 期望 \ 实际 | answer | clarify |
| --- | --- | --- |
| answer | 5 | 1 |
| clarify | 0 | 0 |
| refuse | 0 | 0 |
## 分题型

| 题型 | 题目数 | 可判定题 | EX |
| --- | --- | --- | --- |
| simple | 6 | 6 | 66.7% |

## 失败清单（前 20 条）

- `ec-003` [simple] 列出所有越南供应商的名称，按供应商编号升序。
  - status=ok  error=None
  - 生成 SQL：`SELECT s.name FROM suppliers s WHERE s.country = 'Vietnam' ORDER BY s.supplier_id ASC;`
  - 差异：row_count_diff pred=0 gold=7
- `ec-006` [simple] 查询价格在 200 到 600 元之间（含边界）且在售的商品名称和价格，按商品编号升序。
  - status=clarified  error=None
  - 生成 SQL：``

## 特殊题明细（澄清 / 拒绝）
