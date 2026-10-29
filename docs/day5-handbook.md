# Day 5 实施手册 — 第三库 + A4（缓存/路由）+ 全量消融 + 人工抽评

> 前置：Day 4 已收口（A3 两组数字、gate 写操作规则、report 四指标已落地）。
> 本手册代码块已按项目实际导入约定（`from src.datapilot.*`）核对过。
> **纪律提醒：本日所有新 run 用新 run_id；任何配置/prompt 改动后禁止续跑旧 run_id。**

## 0. 开工前必读：今天为什么做这三件事（15 分钟）

1. **第三库（自建电商）是防污染论据。** Chinook/Sakila 是公开教学库，模型训练语料里大概率见过——你前四天的 EX 里有多少是"背过"的成分，无法证伪。**自建 schema 是模型绝对没见过的**，在它上面的 EX 才是泛化能力的下限估计。面试被问"你的评测会不会被数据污染"时，这一库就是答案。
2. **A4（缓存+路由）是成本工程的故事。** 注意一个诚实前提：**temperature=0 下缓存对单次全量评测的 EX/成本几乎无影响**（首轮全 miss）。缓存的价值在开发循环（反复调 prompt 重跑）和 demo；路由的价值才是单次评测里的真实成本削减，代价是简单题可能的 EX 回退——**这个 tradeoff 必须量出来，不许只讲收益**。
3. **消融矩阵是整张脸。** 前四天的所有数字都是孤证，A0–A4 × 3 库的表才是"每个组件的功过"的最终呈堂证供。**全量数字出来前，README 里不许写任何结论性句子。**

## 0.5 Day 4 复盘的两个待决事项（今天必须给答案，15 分钟）

Day 4 的 A3（gate + verifier）跑完后留下两个**没有结论**的洞，今天扩到第三库时会再遇到，先想清楚：

**① verifier 存废（重要）。** A3 三组 run 的实测：`verify_fixed = 0`，`verify 误杀 = 0`。
也就是说 verifier 到现在为止**一题都没救回来**，但它买到了"没有误伤"（0 误杀），
代价是 token +150%、单题成本 +46%~82%。它可能三种命运：

- **保留**：它拦截的是"错误自信"，而当前 50 题样本里这类题只有 1 道（sa-015）——样本太小，
  不足以否定它。**扩到第三库后若 verify_fixed 仍为 0，就该在消融表里如实写"verifier 未产生收益，
  建议小规模场景不启用"**——这是一个比"它涨了 2 个点"更有价值的结论。
- **降级**：砍掉 LLM judge，只留 `deterministic_flags`（零成本：整列 NULL / 全 NULL / 截断），
  做成一个低成本 guard 挂在 execute 之后。省掉全部 verify 的 token。
- **改造**：当前 verify 只看"结果与题干"，看不到"表是不是全"——Day 4 v3 修复已经证明，
  真正救回 sa-015 的是 **escalate（扩大 schema）而不是 repair**。若把 verify 的 wrong
  直接映射到 escalate+全SELECT，收益形态会更漂亮。

推荐保留到第三库跑完再定，**但睡前必须给出 actionable 的决策规则**（决策树见 §3 末尾）。

**② gate 的 clarify 门槛（次要但会重复踩）。** sakila sa-003 被 gate 判成 clarify 而丢题
（题面已写明"按标题升序、取前 20 部"，口径是全的）→ `gate_false_kill = 1`。
clarify 的代价是直接丢掉一道可答题，比 answer 后答错的代价更高。
**gate 的 fail-open 纪律目前只覆盖了"解析失败/非法 action"，没有覆盖"拿不准该 answer 还是 clarify"。
今天扩题后在 grep 第三库的 clarify 案例时，顺手把 GATE_USER 里的 clarify 门槛收紧一条：
"题面已给出排序方式、取数范围、聚合口径的，即便存在多种合理解释，也判 answer"。**

> 提醒：虽然 `prompt_fingerprint()` 现在仍写死 a0.SYSTEM，gate/verify 的 prompt 并不在指纹内——
> 这条已知债在 Day 5 收尾前必须还掉，否则改了 gate prompt 还用同一个 run_id 续跑，
> 会静默混入两次不同配置的结果。

## 1. 第三库：自建电商 schema（2.5 小时，今天最重的活）

### 1.1 建库脚本（完整可运行）

`scripts/build_ecommerce_db.py`（新建，已实测可跑）：

```python
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
```

```bash
python scripts/build_ecommerce_db.py
# 预期输出含 users=500, orders=3000 等；GMV 一个确定的大数
```

**设计意图（写进日报的"决策"栏）：**

- `order_items.unit_price` 是成交价快照，与 `products.price`（现价）**刻意不一致**——"按现价算销售额"是陷阱题素材；
- `orders.status` 五态，成交口径 = `paid/shipped/completed`——不算取消/退款是陷阱题素材；
- `shipments.delivered_at` 可空 + `coupon_redemptions` 纯中间表——分别是 NULL 处理题和 FK 扩展题素材；
- **确定性 seed=42**：任何人重跑逐字节一致，gold_result 才可复现。

### 1.2 中文业务口径文档（30 分钟）

`data/benchmarks/ecommerce_glossary.md`（新建）——这既是出题依据，也是面试时"业务口径管理"的展示物：

```markdown
# 电商库业务口径（出题与判题的唯一标准）

- **GMV**：成交口径订单（orders.status ∈ paid/shipped/completed）的 payments.amount 求和。
  cancelled / refunded 不计。
- **客单价**：GMV ÷ 成交订单数（不是 ÷ 全部订单数）。
- **复购用户**：成交订单数 ≥ 2 的用户。
- **活跃用户**：近 90 天内有成交订单的用户（库内最大日期为"今天"）。
- **动销率**：有成交订单的商品数 ÷ 在售（status='on'）商品总数。
- **销售额陷阱**：销售额 = order_items.unit_price × quantity（成交快照），
  不是 products.price（现价，会变）。
```

### 1.3 出题（2 小时，今天的瓶颈工序）

`data/benchmarks/ecommerce_v0.jsonl`，**60 题底线 / 80 题目标**。分布：

| 题型 | 数量 | 说明 |
| --- | --- | --- |
| simple | 10 | 单表过滤 |
| aggregation | 12 | GROUP BY / HAVING |
| join | 12 | 2–4 表 |
| nested | 9 | 子查询 / NOT IN / EXISTS |
| ambiguous | 10 | 全部落在 glossary 的口径词上（"活跃用户"不说时间窗等） |
| adversarial | 7 | 写操作伪装（"把退款单删了再算 GMV"）、不存在的实体（"物流满意度评分"——reviews 是商品评分）、现价陷阱的诱导 |

加上存量后全局：110 题，其中歧义 15、陷阱 10——**恰好达到总手册 150 题要求的特殊题密度**。题量 110 vs 150 的缺口是有意的取舍：60 道经过 verify-gold 的题 > 100 道没验证的题，写进日报"决策"栏。

**出题纪律（与 Day 2 相同，不重复解释）：**

- 每题先写 `expected_behavior` 和 notes（标注意图），再写 gold_sql；
- 写完必须 `python -m src.datapilot.cli verify-gold --dataset data/benchmarks/ecommerce_v0.jsonl`，200 行截断警告必须清零（回想 sa-003 教训）；
- `python -m src.datapilot.eval.gold_tables data/benchmarks/ecommerce_v0.jsonl` 回填 gold_tables；
- **至少 2 道 nested 题的 gold_sql 用 WITH 写**——CTE 抽取路径至今只有单测覆盖（Day 2 遗留）；
- order_sensitive 按题面语义手工标（不是按 gold_sql 有没有 ORDER BY 机械标，Day 2 教训）。



**增加业务口径（后期可以放入一个文件中，让system_prompt 去读取）**

a0.py 增加

```python
SYSTEM = """你是一名资深的 SQLite 数据分析师，任务是把用户的问题翻译成一条可执行的 SQLite 查询。

业务口径（必须严格遵守）：
- 商品的"在售"状态值是 status='on'（不是中文'在售'），"下架"是 status='off'。
- "成交订单"指 orders.status IN ('paid','shipped','completed')，cancelled/refunded 不算。
- "GMV/成交总金额"指成交订单的 payments.amount 求和（不是 order_items 的金额）。


规则：
1. 只允许使用下面 schema 中出现的表和列，禁止臆造表名或列名。
2. 只生成一条查询语句，可以使用 CTE（WITH）。禁止任何写操作。
3. 不要输出 SQL 之外的任何解释文字。
4. 必须严格输出如下 JSON：
{"sql": "...", "tables_used": ["表名"], "assumptions": ["你对题意做出的任何假设"]}
"""
```



### 1.4 第三库的 headroom 红线（先跑 A0！）

```bash
python -m src.datapilot.cli eval --config a0 --dataset data/benchmarks/ecommerce_v0.jsonl --run-id a0_ecommerce
```

**A0 EX ≥ 85% → 停，加难度 3 的题再回来。不许在太易的库上跑消融。**（Day 1 的 Chinook 100% 教训。）

## 2. A4 = A3 + 缓存 + 路由（2 小时）

### 2.1 缓存（完整新建 `src/datapilot/llm/cache.py`）

```python
"""LLM 精确缓存：key = sha256(model + system + user + temperature)。
temperature=0 时命中即逐字节一致——缓存不改变 EX，只改变成本与延迟。

诚实声明（面试别吹错）：单次全量评测首轮全 miss，缓存的价值在
① 开发循环（调 prompt 后重跑，未受影响的问题白嫖）；
② 崩溃续跑；③ demo 现场。单次消融 run 的成本削减来自路由，不是缓存。
"""
from __future__ import annotations

import hashlib
import sqlite3
import threading
from pathlib import Path

_LOCK = threading.Lock()  # runner 4 线程共享一个缓存文件，写必须串行


class LLMCache:
    def __init__(self, path: str | Path):
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS cache (k TEXT PRIMARY KEY, v TEXT)")
        self._conn.commit()
        self.hits = 0
        self.misses = 0

    @staticmethod
    def key(model: str, system: str, user: str, temperature: float) -> str:
        raw = f"{model}{temperature}{system}{user}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get(self, k: str) -> str | None:
        row = self._conn.execute("SELECT v FROM cache WHERE k=?", (k,)).fetchone()
        if row is None:
            self.misses += 1
            return None
        self.hits += 1
        return row[0]

    def put(self, k: str, v: str) -> None:
        with _LOCK:
            self._conn.execute("INSERT OR REPLACE INTO cache VALUES (?,?)", (k, v))
            self._conn.commit()

    def close(self) -> None:
        # Windows 上不 close 会占着文件句柄，删缓存文件/清理临时目录时报 WinError 32
        self._conn.close()
```

### 2.2 接入 LLMClient（补丁，`src/datapilot/llm/client.py` 改三处）

```python
# ① __init__ 加参数（改后签名，cache_path=None 时行为与现在逐字节一致）：
def __init__(self, s=settings, cache_path: str | None = None):
    self.s = s
    self._client = OpenAI(api_key=s.api_key, base_url=s.base_url)
    from src.datapilot.llm.cache import LLMCache  # 函数内 import，无缓存时零依赖
    self._cache = LLMCache(cache_path) if cache_path else None

# ② chat_json 里 self._call(kwargs) 之前插入：
        cache_key = None
        if self._cache is not None:
            cache_key = self._cache.key(kwargs["model"], system, user,
                                        kwargs["temperature"])
            hit = self._cache.get(cache_key)
            if hit is not None:
                return LLMResult(text=hit, model=kwargs["model"],
                                 in_tokens=0, out_tokens=0,
                                 cost_cny=0.0,
                                 latency_ms=round((time.perf_counter() - t0) * 1000))
#    命中记 0 token/0 成本——缓存命中本来就没调 API，账必须如实记

# ③ 拿到 resp 之后、return 之前插入：
        if self._cache is not None and cache_key is not None:
            self._cache.put(cache_key, resp.choices[0].message.content or "")
```

### 2.3 路由（两处补丁 + settings 加字段）

`config.py` 的 Settings 类里追加（允许不配，退化为同模型）：

```python
    model_small: str | None = None        # DP_MODEL_SMALL；不配则路由退化为同模型
    price_in_per_m_small: float = 0.0     # DP_PRICE_IN_PER_M_SMALL，不配则按主模型价记账
    price_out_per_m_small: float = 0.0
```

> 去阿里云控制台挑一个更便宜的在售模型填进 `.env`；**不配也能跑**，但那样 A4 的
> 路由行就只剩"同模型"的诚实数字——日报里要写明。

`nodes/common_nodes.py` 的 `node_generate` 补丁（difficulty ≤ 1 的题给小模型）：

```python
def node_generate(state: AgentState, client: LLMClient) -> dict:
    user = f"# 数据库 Schema\n{state['schema_text']}\n\n# 用户问题\n{state['question']}"
    # 【A4 路由】简单题给小模型；model_small 未配置时 settings 返回 None → 主模型
    model = None
    if state.get("route_small") and state.get("difficulty", 3) <= 1:
        model = settings.model_small  # None 时 chat_json 回退主模型
    r = client.chat_json(SYSTEM, user, model=model)
    # ……后续不变
```

`client.py` 的成本行补丁（按实际模型选单价，否则路由省的钱在账上看不见）：

```python
        # 成本公式：(输入 token / 1e6) × 输入单价 + (输出 token / 1e6) × 输出单价
        if kwargs["model"] == self.s.model_small and self.s.price_in_per_m_small:
            pin, pout = self.s.price_in_per_m_small, self.s.price_out_per_m_small
        else:
            pin, pout = self.s.price_in_per_m, self.s.price_out_per_m
        cost = (u.prompt_tokens / 1e6) * pin + (u.completion_tokens / 1e6) * pout
```

### 2.4 图与管线接线（三处小补丁）

`graph.py` 的 `_get_client` 改为按缓存路径分键（A2/A3 调用方式不变）：

```python
_clients: dict = {}  # cache_path -> LLMClient；None 键即原单例语义

def _get_client(cache_path: str | None = None) -> LLMClient:
    if cache_path not in _clients:
        _clients[cache_path] = LLMClient(cache_path=cache_path)
    return _clients[cache_path]
```

`build_graph` 签名加可选参数（旧调用 `build_graph(db)` / `build_graph(db, with_reliability=True)` 不受影响）：

```python
def build_graph(checkpoint_db: str, with_reliability: bool = False,
                cfg: dict | None = None):
    cfg = cfg or {}
    cache_path = cfg.get("cache_path")      # 仅 A4 传
    # 函数内所有 _get_client() 调用改为 _get_client(cache_path)
```

`state.py` 追加一个字段：`route_small: bool  # A4：简单题路由小模型`

`eval/configs/a4.yaml`（新建）：

```yaml
pipeline: a4
top_k: 6
repair_max_attempts: 3
cache: true
route_small: true
```

`pipelines/a4.py`（新建，与 a3 的差异处用 ★ 标出）：

```python
# A4 = A3 + 缓存 + 路由。与 a3.py 的差异处用 ★ 标出。
import threading
import time
import uuid

from src.datapilot.graph import build_graph


def graph_answer_a4(q: dict, client=None, cfg: dict | None = None) -> dict:
    cfg = cfg or {}
    t0 = time.perf_counter()
    # ★1 缓存文件按 run 隔离不进这里——跨 run 共享才有开发循环收益，固定文件名
    a4_cfg = dict(cfg)
    if a4_cfg.get("cache"):
        a4_cfg["cache_path"] = "experiments/cache/llm_cache.db"
    app = build_graph(f"checkpoints-{threading.get_ident()}.db",
                      with_reliability=True, cfg=a4_cfg)  # ★2 cfg 进图
    final = app.invoke(
        {
            "question": q["question"], "db_id": q["db_id"],
            "trace_id": f"a4-{q['id']}",
            "top_k": cfg.get("top_k", 6),
            "max_attempts": cfg.get("repair_max_attempts", 3),
            "difficulty": q.get("difficulty", 1),
            "hitl": False,
            "route_small": bool(cfg.get("route_small")),   # ★3 路由开关进 state
            "attempts": 0, "escalated": False, "sql_history": [],
            "verify_retried": False,
            "behavior": "answer", "cost_cny": 0.0, "in_tokens": 0, "llm_calls": 0,
        },
        config={"configurable": {"thread_id": f"a4:{q['id']}:{uuid.uuid4().hex[:8]}"}},
    )
    # ★4 gate 拦截的行为（clarify/refuse）从未执行过 SQL，不能记成 sql_error——
    #    error_rate 的口径是"SQL/执行错误率"，行为误判会污染它（Day 4 a3.py 的实测教训）
    behavior = final.get("behavior", "answer")
    if behavior == "clarify":
        status = "clarified"
    elif behavior == "refuse":
        status = "refused"
    else:
        status = "ok" if final.get("exec_ok") else "sql_error"
    return {
        "status": status,
        "sql": final.get("sql"),
        "tables_used": final.get("retrieved_tables"),
        "assumptions": None,
        "rows": final.get("rows"),
        "columns": final.get("columns"),
        "error": final.get("error") or final.get("give_up_reason"),
        "behavior": final.get("behavior", "answer"),
        "llm_calls": final.get("llm_calls", 0),
        "cost_cny": final.get("cost_cny", 0.0),
        "retrieved_tables": final.get("retrieved_tables"),
        "extra": {
            "in_tokens": final.get("in_tokens"),
            "attempts": final.get("attempts"),
            "escalated": final.get("escalated"),
            "first_rows": final.get("first_rows"),
            "diagnosis": final.get("diagnosis"),
            "error_code": final.get("error_code"),
            "gate": final.get("gate"),
            "verify": final.get("verify"),
        },
    }
```

`runner.py` 的 `get_pipeline` 加分支（注意：文件在 `eval/runner.py`，不是 cli.py）：

```python
    if name == "a4":
        from src.datapilot.pipelines.a4 import graph_answer_a4
        return lambda q: graph_answer_a4(q, cfg=cfg)
```

`.gitignore` 追加一行：`experiments/cache/`

### 2.5 A4 验收

```bash
python -m src.datapilot.cli eval --config a4 --dataset data/benchmarks/ecommerce_v0.jsonl --limit 6 --run-id a4_smoke
# 立即同 run_id 重跑一次：第二次应全部缓存命中（cost 增量≈0、in_tokens 增量≈0）
python -m src.datapilot.cli eval --config a4 --dataset data/benchmarks/ecommerce_v0.jsonl --limit 6 --run-id a4_smoke
```

**验收口径：A4 与 A3 的 EX 差即路由的代价；第二次运行的成本增量即缓存的收益。两个数字都要进日报，不许只报后者。**

## 3. 全量消融（2 小时，主要是等待）

矩阵：A0/A1/A2/A3/A4 × chinook/sakila/ecommerce。chinook/sakila 的 A0–A3 已有封存 run，**只补 A4 和 ecommerce 全列**：

```bash
for cfg in a0 a1 a2 a3 a4; do
  python -m src.datapilot.cli eval --config $cfg --dataset data/benchmarks/ecommerce_v0.jsonl --run-id ecommerce_${cfg}
done
python -m src.datapilot.cli eval --config a4 --run-id a4_chinook
python -m src.datapilot.cli eval --config a4 --dataset data/benchmarks/sakila_v0.jsonl --run-id a4_sakila


# powershell 写法
foreach ($cfg in 'a0','a1','a2','a3','a4') {
  python -m src.datapilot.cli eval --config $cfg `
    --dataset data/benchmarks/ecommerce_v0.jsonl `
    --run-id "ecommerce_$cfg"
}

foreach ($cfg in 'a0','a1','a2','a3','a4') {
  python -m src.datapilot.cli eval --config $cfg `
    --dataset data/benchmarks/sakila_v0.jsonl `
    --run-id "sakila_$cfg"
}

foreach ($cfg in 'a0','a1','a2','a3','a4') {
  python -m src.datapilot.cli eval --config $cfg `
    --dataset data/benchmarks/chinook_v0.jsonl `
    --run-id "chinook_$cfg"
}
```

预算提醒：ecommerce 60–80 题 × 5 配置，A3/A4 单题约 ¥0.009，合计约 ¥3–4。错峰跑，撞 429 就等。

### verifier 存废决策树（全量数字出来当天填，不许拖到 Day 6）

```
样本里"错误自信"题够不够多？——看 A2 vs A3 的 ex_first=True 但 ex=False 的题数
│
├─ ≥ 5 题（样本足够）
│    └─ verify_fixed > 0 且 verify_false_alarm < verify_fixed  → 保留，写清净收益与单题成本
│    └─ verify_fixed = 0                                      → 写"verifier 未产生收益"（诚实负结果）
│                                                               并按 §0.5 的"降级"方案砍 LLM judge
└─ < 5 题（样本不够）
     └─ 不许下任何结论。写明"当前评测集对该组件的检验力不足"，
        把它列进项目的已知局限——这比含糊地说"有一定效果"强一百倍
```

判 ground truth 的方法（`ex_first=True → ex=False` 就是"首轮看着对了、最终反而错了"，
即 verifier 打回流造成的净损失；`verify_fixed` 是净收益）：

```python
import json
recs = [json.loads(l) for l in open("experiments/runs/a3_ecommerce/results.jsonl", encoding="utf-8") if l.strip()]
kill = [r["id"] for r in recs if r.get("ex_first") is True and r.get("ex") is False]
fixed = [r["id"] for r in recs if r.get("ex_first") is False and r.get("ex") is True]
print("错误自信样本数:", len(kill), "| verify 净收益:", len(fixed), "| 误杀:", kill)
```

## 4. 消融报告生成器（1 小时）

`scripts/ablation_report.py`（新建，完整可运行）：

```python
"""汇总 experiments/runs/ 下指定 run，生成 reports/ablation.md。
用法：python scripts/ablation_report.py
"""
import json
from pathlib import Path

RUNS = [  # (配置, 库, run_id)——与第 3 节的 run_id 一一对应，改了 run_id 这里同步改
    ("a0", "chinook", "a0_chinook_fix"), ("a0", "sakila", "a0_sakila_fix"),
    ("a1", "chinook", "a1_chinook_fix"), ("a1", "sakila", "a1_sakila_fix"),
    ("a2", "chinook", "a2_chinook_v3"), ("a2", "sakila", "a2_sakila_v3"),
    ("a3", "chinook", "a3_chinook_v3"), ("a3", "sakila", "a3_sakila_v3"),
    ("a4", "chinook", "a4_chinook"), ("a4", "sakila", "a4_sakila"),
] + [(c, "ecommerce", f"{c}_ecommerce") for c in ("a0", "a1", "a2", "a3", "a4")]

FIELDS = [("ex", "EX"), ("ex_first", "首轮EX"), ("repair_gain", "修复增益"),
          ("schema_recall", "召回率"), ("behavior_ok", "行为正确率"),
          ("gate_false_kill", "gate误杀"), ("verify_fixed", "verify修复"),
          ("verify_false_alarm", "verify误杀"), ("avg_in_tokens", "均token"),
          ("cost_per_q_cny", "单题成本"), ("latency_p95_ms", "P95ms")]


def main() -> None:
    import sys
    # 脚本从 scripts/ 启动时 sys.path[0]=scripts/，必须把项目根（含 src 包）加进去
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from src.datapilot.eval.metrics import aggregate

    rows = []
    for cfg_name, db, run_id in RUNS:
        p = Path("experiments/runs") / run_id / "results.jsonl"
        if not p.exists():
            rows.append((cfg_name, db, None))
            continue
        recs = [json.loads(l) for l in p.open(encoding="utf-8") if l.strip()]
        rows.append((cfg_name, db, aggregate(recs)))

    dbs = ["chinook", "sakila", "ecommerce"]
    lines = ["# 消融矩阵（自动生成，数据可溯源到 run_id）", ""]
    for db in dbs:
        lines.append(f"## {db}")
        lines.append("| 配置 | " + " | ".join(n for _, n in FIELDS) + " |")
        lines.append("| --- |" + " --- |" * len(FIELDS))
        for cfg_name, rdb, s in rows:
            if rdb != db:
                continue
            if s is None:
                lines.append(f"| {cfg_name} | " + " | ".join(["缺"] * len(FIELDS)) + " |")
                continue
            cells = []
            for k, _ in FIELDS:
                v = s.get(k)
                if v is None:
                    cells.append("—")
                elif k in ("ex", "ex_first", "repair_gain", "schema_recall",
                           "behavior_ok"):
                    cells.append(f"{v:.1%}")
                elif k == "cost_per_q_cny":
                    cells.append(f"¥{v:.4f}")
                else:
                    cells.append(str(v))
            lines.append(f"| {cfg_name} | " + " | ".join(cells) + " |")
        lines.append("")
    out = Path("reports/ablation.md")
    out.write_text("\n".join(lines), encoding="utf-8")
    print("报告：", out.resolve())


if __name__ == "__main__":
    main()
```

> 图表可选：`uv add matplotlib` 后自行加"配置×库 EX 分组柱状图"。**表格是底线，图是加分项，不许为了图推迟消融结论。**

## 5. 人工抽评"错误自信率"（1 小时）

定义（写进报告，口径先行）：**结论文本做出了结果集不支持的断言**——把相关说成因果、把样本说成全体、忽略 NULL/截断、给数字编单位/趋势——即计一次错误自信。

`scripts/make_review_sheet.py`（新建，完整可运行）：

```python
"""从指定 run 抽 30 条"答对且给了结论"的记录，生成人工评审表。
用法：python scripts/make_review_sheet.py <run_id> [<run_id>...]
产出：reports/review_sheet.md——人工逐条勾选，勾完统计错误自信率。
"""
import json
import random
import sys
from pathlib import Path


def main(run_ids: list[str]) -> None:
    pool = []
    for rid in run_ids:
        p = Path("experiments/runs") / rid / "results.jsonl"
        for l in p.open(encoding="utf-8"):
            r = json.loads(l)
            # 只抽"答对"的：错答案的结论是另一个指标（失败归因）的事
            if r.get("ex") is True and r.get("behavior") in (None, "answer"):
                r["_run"] = rid
                pool.append(r)
    random.Random(42).shuffle(pool)          # 固定种子：抽样可复现
    sample = pool[:30]
    lines = ["# 错误自信率人工评审表", "",
             "口径：结论文本做出结果集不支持的断言即计一次（相关当因果 / "
             "样本当全体 / 忽略 NULL 或截断 / 编造单位与趋势）。", ""]
    for i, r in enumerate(sample, 1):
        lines += [
            f"## {i}. `{r['id']}`（{r['_run']}）",
            f"- 问题：{r['question']}",
            f"- SQL：`{(r.get('sql') or '')[:200]}`",
            f"- 结果行数：{r.get('row_count')}",
            "- [ ] 结论有过度断言（勾选即计一次错误自信）",
            "- 备注：", ""]
    Path("reports/review_sheet.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"已抽样 {len(sample)} 条 → reports/review_sheet.md")


if __name__ == "__main__":
    main(sys.argv[1:] or ["a3_chinook_v3", "a3_sakila_v3", "a3_ecommerce"])
```

评完把"错误自信率 = 勾选数 / 30"写进日报——**这个数字无论高低都是结论**：低，说明 composer 的保守写法有效；高，说明"答对"里藏着可信度的坑，这是比 EX 更锋利的卖点。

## 6. 收尾验收清单

- [ ] ecommerce.db 建成且 GMV 冒烟可算；`ecommerce_glossary.md` 落盘
- [ ] `ecommerce_v0.jsonl` ≥60 题，verify-gold 无截断警告，gold_tables 已回填，≥2 道 CTE 题
- [ ] `a0_ecommerce` EX < 85%（headroom 成立）才允许继续；否则先加难题
- [ ] A4 缓存验收：同 run_id 第二次运行成本增量 ≈ 0
- [ ] 15 个 run 全部落盘（缺的在消融表里标"缺"，不许留空格假装跑过）
- [ ] `reports/ablation.md` 生成；**至少一条"某改动没用甚至变差"的诚实结论**
- [ ] `reports/review_sheet.md` 30 条评完，错误自信率有数字
- [ ] 日报：消融表 + 三条结论 + 已知局限（110 vs 150 的取舍、路由若无小模型配置的退化声明）

## 7. 砍单顺序（时间不够时从上往下砍）

1. 砍 matplotlib 图表（表格即可）
2. ecommerce 题量砍到 60 底线
3. 砍路由（a4.yaml 去掉 route_small，A4 只剩缓存——如实写"路由未实测"）
4. 人工抽评砍到 15 条
5. **不许砍**：verify-gold、headroom 红线、消融表的诚实结论
