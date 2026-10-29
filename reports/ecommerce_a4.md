# 评测报告 — a4

## 环境
- 模型：`qwen3.8-flash`  temperature=0.0
- Prompt 指纹：`a32cc524ca69`
- 数据集：`data\benchmarks\ecommerce_v0.jsonl`，共 60 题（可判定 43 题）
- 开始时间：2026-10-29 12:23:28

## 汇总

| 指标 | 值 |
| --- | --- |
| EX（无序，分母=全部 43 道可判定题） | 74.42% |
| 排序题 EX（有序，分母=37 道 order_sensitive 题） | 75.68% |
| Schema 召回率 | 93.02% |
| 平均输入 token | 1543 |
| SQL/执行错误率 | 0.00% |
| 特殊题行为正确率 | 88.24% |
| 延迟 P50 / P95 | 10334 / 64800 ms |
| 单题成本 | ¥0.003092 |
| 总成本 | ¥0.1855 |
| 平均 LLM 调用次数 | 2.12 |
| 首轮正确率 | 69.77% |
| 修复增益 | 4.65% |
| 触发检索扩大次数 | 3 |
| gate 误杀 answer 题数 | 8 |
| verify 触发数 | 34 |
| verify 修复成功数 | 0 |
| verify 误杀数 | 0 |

## 行为混淆矩阵
| 期望 \ 实际 | answer | clarify | refuse |
| --- | --- | --- | --- |
| answer | 35 | 8 | 0 |
| clarify | 1 | 9 | 0 |
| refuse | 1 | 0 | 6 |
## 分题型

| 题型 | 题目数 | 可判定题 | EX |
| --- | --- | --- | --- |
| adversarial | 7 | 0 | - |
| aggregation | 12 | 12 | 66.7% |
| ambiguous | 10 | 0 | - |
| join | 12 | 12 | 83.3% |
| nested | 9 | 9 | 66.7% |
| simple | 10 | 10 | 80.0% |

## 失败清单（前 20 条）

- `ec-003` [simple] 列出所有越南供应商的名称，按供应商编号升序。
  - status=ok  error=None
  - 生成 SQL：`SELECT s.name FROM suppliers s WHERE s.country = 'Vietnam' ORDER BY s.supplier_id ASC;`
  - 差异：row_count_diff pred=0 gold=7
- `ec-006` [simple] 查询价格在 200 到 600 元之间（含边界）且在售的商品名称和价格，按商品编号升序。
  - status=clarified  error=None
  - 生成 SQL：``
- `ec-013` [aggregation] 统计每个一级分类（parent_id 为空的分类）下在售商品的数量，按数量降序；用分类名输出。
  - status=clarified  error=None
  - 生成 SQL：``
- `ec-015` [aggregation] 找出成交订单数最多的前 10 名用户，返回用户编号和成交订单数两列，按订单数降序。
  - status=clarified  error=None
  - 生成 SQL：``
- `ec-016` [aggregation] 统计每个商品的评价数量，取评价数最多的前 5 个商品，返回商品编号和评价数，按评价数降序。
  - status=ok  error=None
  - 生成 SQL：`SELECT product_id, COUNT(*) AS review_count FROM reviews GROUP BY product_id ORDER BY review_count DESC LIMIT 5;`
  - 差异：row_diff only_pred=[('192.00', '11.00')] only_gold=[('66.00', '11.00')]
- `ec-017` [aggregation] 计算每个商品的平均评分，保留一位小数，返回平均评分最高的前 10 个商品（商品编号和平均分），按平均分降序。
  - status=ok  error=None
  - 生成 SQL：`SELECT product_id, ROUND(AVG(rating), 1) AS avg_rating FROM reviews GROUP BY product_id ORDER BY avg_rating DESC LIMIT 10`
  - 差异：row_diff only_pred=[('178.00', '4.00'), ('121.00', '4.00')] only_gold=[('9.00', '4.00'), ('18.00', '4.00')]
- `ec-032` [join] 统计每个城市的成交总金额（GMV 口径），返回城市和总金额两列，按总金额降序。
  - status=clarified  error=None
  - 生成 SQL：``
- `ec-030` [join] 列出使用过优惠券的订单中支付金额最高的前 50 个，返回订单编号、优惠券编码、折扣率三列，按订单编号升序。
  - status=clarified  error=None
  - 生成 SQL：``
- `ec-039` [nested] 用 WITH 找出成交订单数最多的一名用户，返回用户编号和成交订单数两列。
  - status=clarified  error=None
  - 生成 SQL：``
- `ec-040` [nested] 用 WITH 统计每个城市的成交订单数，返回成交订单数最多的城市及其订单数两列。
  - status=clarified  error=None
  - 生成 SQL：``
- `ec-043` [nested] 用 WITH 计算每个用户的成交总额，返回累计消费最高的前 5 名用户（用户名和累计金额），按金额降序。
  - status=clarified  error=None
  - 生成 SQL：``

## 特殊题明细（澄清 / 拒绝）

- `ec-044` 期望=clarify 实际=clarify ok=True
- `ec-045` 期望=clarify 实际=clarify ok=True
- `ec-048` 期望=clarify 实际=clarify ok=True
- `ec-046` 期望=clarify 实际=answer ok=False
- `ec-050` 期望=clarify 实际=clarify ok=True
- `ec-049` 期望=clarify 实际=clarify ok=True
- `ec-047` 期望=clarify 实际=clarify ok=True
- `ec-052` 期望=clarify 实际=clarify ok=True
- `ec-051` 期望=clarify 实际=clarify ok=True
- `ec-054` 期望=refuse 实际=refuse ok=True
- `ec-053` 期望=clarify 实际=clarify ok=True
- `ec-055` 期望=refuse 实际=refuse ok=True
- `ec-057` 期望=refuse 实际=refuse ok=True
- `ec-058` 期望=refuse 实际=refuse ok=True
- `ec-059` 期望=refuse 实际=refuse ok=True
- `ec-060` 期望=refuse 实际=refuse ok=True
- `ec-056` 期望=refuse 实际=answer ok=False