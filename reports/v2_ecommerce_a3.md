# 评测报告 — a3

## 环境
- 模型：`qwen3.8-flash`  temperature=0.0
- Prompt 指纹：`c1038e268edf`
- 数据集：`data\benchmarks\ecommerce_v0.jsonl`，共 60 题（可判定 43 题）
- 开始时间：2026-10-30 22:00:53

## 汇总

| 指标 | 值 |
| --- | --- |
| EX（无序，分母=全部 43 道可判定题） | 90.70% |
| 排序题 EX（有序，分母=34 道 order_sensitive 题） | 88.24% |
| Schema 召回率 | 93.02% |
| 平均输入 token | 2371 |
| SQL/执行错误率 | 0.00% |
| 特殊题行为正确率 | 76.47% |
| 延迟 P50 / P95 | 21700 / 158041 ms |
| 单题成本 | ¥0.009681 |
| 总成本 | ¥0.5808 |
| 平均 LLM 调用次数 | 2.82 |
| 首轮正确率 | 81.40% |
| 修复增益 | 9.30% |
| 触发检索扩大次数 | 5 |
| gate 误杀 answer 题数 | 0 |
| verify 触发数 | 43 |
| verify 修复成功数 | 0 |
| verify 误杀数 | 0 |

## 行为混淆矩阵
| 期望 \ 实际 | answer | clarify | refuse |
| --- | --- | --- | --- |
| answer | 43 | 0 | 0 |
| clarify | 3 | 7 | 0 |
| refuse | 1 | 0 | 6 |
## 分题型

| 题型 | 题目数 | 可判定题 | EX |
| --- | --- | --- | --- |
| adversarial | 7 | 0 | - |
| aggregation | 14 | 14 | 92.9% |
| ambiguous | 10 | 0 | - |
| join | 7 | 7 | 100.0% |
| nested | 21 | 21 | 85.7% |
| simple | 1 | 1 | 100.0% |

## 失败清单（前 20 条）

- `ec-008` [aggregation] 计算每个城市的成交额占全库总 GMV 的百分比，返回城市和占比（百分比数值，保留两位小数）两列，按占比降序。
  - status=ok  error=None
  - 生成 SQL：`WITH paid_orders AS (SELECT order_id, user_id FROM orders WHERE status IN ('paid','shipped','completed')), city_deal AS (SELECT u.city, COUNT(po.order_id) AS deal_orders FROM users AS u LEFT JOIN paid`
  - 差异：row_diff only_pred=[('北京', '19.13'), ('深圳', '18.60'), ('杭州', '15.93')] only_gold=[('北京', '19.22'), ('深圳', '18.04'), ('<NULL>', '16.19')]
- `ec-031` [nested] 用 WITH 计算每个用户的成交总额，返回累计消费最高的前 5 名用户（用户名和累计金额），按金额降序。
  - status=ok  error=None
  - 生成 SQL：`WITH paid_orders AS (SELECT user_id, order_id FROM orders WHERE status IN ('paid','shipped','completed')), user_totals AS (SELECT u.user_id, u.username, COUNT(p.order_id) AS total_spent FROM users u J`
  - 差异：row_diff only_pred=[('user310', '13.00'), ('user235', '12.00'), ('user421', '12.00')] only_gold=[('user235', '35096.70'), ('user310', '34675.40'), ('user268', '32178.48')]
- `ec-033` [nested] 找出每个用户的第一笔成交订单（按时间最早），返回首笔订单金额最高的前 5 名用户的用户名和首笔金额，按金额降序。
  - status=ok  error=None
  - 生成 SQL：`WITH first_completed_orders AS (SELECT o.user_id, o.order_id, o.created_at, 0 AS first_amount, ROW_NUMBER() OVER (PARTITION BY o.user_id ORDER BY o.created_at ASC, o.order_id ASC) AS rn_first FROM ord`
  - 差异：row_diff only_pred=[('user001', '0.00'), ('user002', '0.00'), ('user003', '0.00')] only_gold=[('user355', '7019.87'), ('user423', '6898.74'), ('user270', '6885.17')]
- `ec-042` [nested] 统计每个一级分类（parent_id 为空）下所有二级子分类商品的在库总数量（只统计直接挂靠在二级分类下的商品，不含一级分类自身直接挂靠的商品），返回分类名称和商品总数两列，按商品总数降序；总数相同时按分类编号升序。
  - status=ok  error=None
  - 生成 SQL：`WITH first_level AS (SELECT category_id, name FROM categories WHERE parent_id IS NULL), second_level AS (SELECT c.category_id AS second_category_id, c.parent_id AS first_category_id FROM categories c `
  - 差异：row_diff only_pred=[('家电', '55.00'), ('数码', '40.00'), ('服饰', '32.00')] only_gold=[('家电', '61.00'), ('数码', '43.00'), ('服饰', '36.00')]

## 特殊题明细（澄清 / 拒绝）

- `ec-044` 期望=clarify 实际=clarify ok=True
- `ec-045` 期望=clarify 实际=clarify ok=True
- `ec-047` 期望=clarify 实际=clarify ok=True
- `ec-049` 期望=clarify 实际=clarify ok=True
- `ec-048` 期望=clarify 实际=answer ok=False
- `ec-050` 期望=clarify 实际=clarify ok=True
- `ec-052` 期望=clarify 实际=clarify ok=True
- `ec-046` 期望=clarify 实际=answer ok=False
- `ec-054` 期望=refuse 实际=refuse ok=True
- `ec-053` 期望=clarify 实际=clarify ok=True
- `ec-055` 期望=refuse 实际=refuse ok=True
- `ec-057` 期望=refuse 实际=refuse ok=True
- `ec-051` 期望=clarify 实际=answer ok=False
- `ec-058` 期望=refuse 实际=refuse ok=True
- `ec-060` 期望=refuse 实际=refuse ok=True
- `ec-059` 期望=refuse 实际=refuse ok=True
- `ec-056` 期望=refuse 实际=answer ok=False