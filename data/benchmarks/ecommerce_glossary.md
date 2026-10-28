# 电商库业务口径（出题与判题的唯一标准）

- **GMV**：成交口径订单（orders.status ∈ paid/shipped/completed）的 payments.amount 求和。cancelled / refunded 不计。
- **客单价**：GMV ÷ 成交订单数（不是 ÷ 全部订单数）。
- **复购用户**：成交订单数 ≥ 2 的用户。
- **活跃用户**：近 90 天内有成交订单的用户（库内最大日期为"今天"）。
- **动销率**：有成交订单的商品数 ÷ 在售（status='on'）商品总数。
- **销售额陷阱**：销售额 = order_items.unit_price × quantity（成交快照），不是 products.price（现价，会变）。