"""自建电商库：模型训练语料里不存在的 schema，是泛化能力的下限估计。
确定性种子（seed=42）——任何人重跑得到逐字节一致的数据，gold 才可复现。

运行：python scripts/build_ecommerce_db.py
产出：data/dbs/ecommerce.db
"""
import random
import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parent.parent / "data" / "dbs" / "ecommerce.db"

DDL = """
CREATE TABLE users (
    user_id INTEGER PRIMARY KEY, username TEXT NOT NULL, email TEXT,
    city TEXT, registered_at TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'active'
    -- status ∈ {active, churned}
);
CREATE TABLE categories (
    category_id INTEGER PRIMARY KEY, name TEXT NOT NULL,
    parent_id INTEGER REFERENCES categories(category_id)  -- 自引用，出嵌套题的素材
);
CREATE TABLE suppliers (
    supplier_id INTEGER PRIMARY KEY, name TEXT NOT NULL, country TEXT
);
CREATE TABLE products (
    product_id INTEGER PRIMARY KEY, name TEXT NOT NULL,
    category_id INTEGER REFERENCES categories(category_id),
    supplier_id INTEGER REFERENCES suppliers(supplier_id),
    price REAL NOT NULL, cost REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'on'  -- on=在售, off=下架
);
CREATE TABLE coupons (
    coupon_id INTEGER PRIMARY KEY, code TEXT UNIQUE,
    discount_pct REAL NOT NULL, valid_from TEXT, valid_to TEXT
);
CREATE TABLE orders (
    order_id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id),
    status TEXT NOT NULL,  -- paid/shipped/completed/cancelled/refunded
    created_at TEXT NOT NULL,
    coupon_id INTEGER REFERENCES coupons(coupon_id)  -- 可空：大部分单没用券
);
CREATE TABLE order_items (
    order_id INTEGER NOT NULL REFERENCES orders(order_id),
    product_id INTEGER NOT NULL REFERENCES products(product_id),
    quantity INTEGER NOT NULL, unit_price REAL NOT NULL,  -- 成交价快照，≠ products.price
    PRIMARY KEY (order_id, product_id)
);
CREATE TABLE payments (
    payment_id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(order_id),
    method TEXT, amount REAL NOT NULL, paid_at TEXT
);
CREATE TABLE shipments (
    shipment_id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(order_id),
    carrier TEXT, shipped_at TEXT,
    delivered_at TEXT  -- 可空：未签收——"未送达订单"题的素材
);
CREATE TABLE reviews (
    review_id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id),
    product_id INTEGER NOT NULL REFERENCES products(product_id),
    rating INTEGER NOT NULL,  -- 1..5
    content TEXT, created_at TEXT NOT NULL
);
-- 纯中间表：无外键就联不上 coupons 和 orders——FK 一跳扩展存在的意义
CREATE TABLE coupon_redemptions (
    coupon_id INTEGER NOT NULL REFERENCES coupons(coupon_id),
    order_id INTEGER NOT NULL REFERENCES orders(order_id),
    user_id INTEGER NOT NULL REFERENCES users(user_id),
    redeemed_at TEXT NOT NULL,
    PRIMARY KEY (coupon_id, order_id)
);
CREATE TABLE inventory_logs (
    log_id INTEGER PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(product_id),
    change INTEGER NOT NULL, reason TEXT, created_at TEXT NOT NULL
);
"""

# 成交价口径：GMV 只算 paid/shipped/completed；cancelled/refunded 不算。
SETTLED = ("paid", "shipped", "completed")


def main() -> None:
    rng = random.Random(42)
    DB.parent.mkdir(parents=True, exist_ok=True)
    if DB.exists():
        DB.unlink()
    conn = sqlite3.connect(DB)
    conn.executescript("PRAGMA foreign_keys=ON;\n" + DDL)
    cur = conn.cursor()

    cities = ["杭州", "上海", "北京", "深圳", "成都", None]
    users = [(i, f"user{i:03d}", f"u{i}@x.com", rng.choice(cities),
              f"202{rng.randint(3, 4)}-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}",
              "churned" if rng.random() < 0.15 else "active")
             for i in range(1, 501)]
    cur.executemany("INSERT INTO users VALUES (?,?,?,?,?,?)", users)

    cats = [(1, "数码", None), (2, "家电", None), (3, "服饰", None),
            (4, "手机", 1), (5, "耳机", 1), (6, "冰箱", 2), (7, "洗衣机", 2),
            (8, "男装", 3), (9, "女装", 3)]
    cur.executemany("INSERT INTO categories VALUES (?,?,?)", cats)
    cur.executemany("INSERT INTO suppliers VALUES (?,?,?)",
                    [(i, f"供应商{chr(64 + i)}", rng.choice(["中国", "越南", "马来西亚"]))
                     for i in range(1, 21)])

    products = [(i, f"商品{i:03d}", rng.randint(1, 9), rng.randint(1, 20),
                 round(rng.uniform(9.9, 999.0), 2), 0, "on") for i in range(1, 201)]
    products = [(pid, n, c, s, p, round(p * rng.uniform(0.4, 0.7), 2), st)
                for pid, n, c, s, p, _, st in products]
    # 故意下架 10%：「在售商品」题的过滤条件素材
    products = [(pid, n, c, s, p, cost, "off" if pid % 10 == 0 else st)
                for pid, n, c, s, p, cost, st in products]
    cur.executemany("INSERT INTO products VALUES (?,?,?,?,?,?,?)", products)

    cur.executemany("INSERT INTO coupons VALUES (?,?,?,?,?)",
                    [(i, f"CP{i:03d}", rng.choice([5, 10, 15, 20]),
                      "2024-01-01", "2025-12-31") for i in range(1, 31)])

    statuses = ["completed"] * 55 + ["shipped"] * 10 + ["paid"] * 10 + \
               ["cancelled"] * 15 + ["refunded"] * 10
    # 优惠券折扣率一次取全，别在订单循环里反复查表
    disc_map = {cid: pct for cid, pct in
                cur.execute("SELECT coupon_id, discount_pct FROM coupons")}
    pay_id = ship_id = 0
    order_rows, item_rows, pay_rows, ship_rows, red_rows = [], [], [], [], []
    for oid in range(1, 3001):
        uid = rng.randint(1, 500)
        st = rng.choice(statuses)
        day = f"202{rng.randint(4, 5)}-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}"
        used_coupon = rng.random() < 0.2 and st in SETTLED
        cid = rng.randint(1, 30) if used_coupon else None
        order_rows.append((oid, uid, st, day, cid))
        total = 0.0
        for prod in rng.sample(range(1, 201), rng.randint(1, 4)):
            qty = rng.randint(1, 3)
            price = products[prod - 1][4]
            item_rows.append((oid, prod, qty, price))
            total += qty * price
        if st in SETTLED:
            pay_id += 1
            if cid:
                total *= 1 - disc_map[cid] / 100
            pay_rows.append((pay_id, oid, rng.choice(["alipay", "wechat", "card"]),
                             round(total, 2), day))
        if st in ("shipped", "completed"):
            ship_id += 1
            delivered = None if (st == "shipped" or rng.random() < 0.1) else day
            ship_rows.append((ship_id, oid, rng.choice(["顺丰", "中通", "圆通"]),
                              day, delivered))
        if used_coupon:
            red_rows.append((cid, oid, uid, day))
    cur.executemany("INSERT INTO orders VALUES (?,?,?,?,?)", order_rows)
    cur.executemany("INSERT INTO order_items VALUES (?,?,?,?)", item_rows)
    cur.executemany("INSERT INTO payments VALUES (?,?,?,?,?)", pay_rows)
    cur.executemany("INSERT INTO shipments VALUES (?,?,?,?,?)", ship_rows)
    cur.executemany("INSERT INTO coupon_redemptions VALUES (?,?,?,?)", red_rows)

    reviews = [(i, rng.randint(1, 500), rng.randint(1, 200), rng.randint(1, 5),
                rng.choice(["不错", "一般", "差", "很好", None]),
                f"2025-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}")
               for i in range(1, 1201)]
    cur.executemany("INSERT INTO reviews VALUES (?,?,?,?,?,?)", reviews)
    logs = [(i, rng.randint(1, 200), rng.randint(-50, 100),
             rng.choice(["入库", "出库", "盘点调整"]),
             f"2025-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}")
            for i in range(1, 801)]
    cur.executemany("INSERT INTO inventory_logs VALUES (?,?,?,?,?)", logs)

    conn.commit()
    n = {t: cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
         for t in ["users", "products", "orders", "order_items", "payments",
                   "shipments", "reviews", "coupon_redemptions"]}
    print("ecommerce.db 建成：", n)
    # 冒烟：GMV 口径必须可算
    gmv = cur.execute(
        "SELECT ROUND(SUM(amount),2) FROM payments").fetchone()[0]
    print(f"全库 GMV（payments.amount 求和）: {gmv}")
    conn.close()


if __name__ == "__main__":
    main()
