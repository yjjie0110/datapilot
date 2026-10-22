# Day 2 实施手册 —— schema 检索与第二个评测库

> 前置：Day 1 已完成（30 题、metrics、runner、A0 数字）。
> 本手册与总手册有一处**刻意的偏离**：把第二个数据库从 Day 5 提前到 Day 2。原因写在第 0 章，先读懂再动手。

---

## 0. 开工前：先处理 Day 1 留下的三笔债（60 分钟，不允许跳过）

### 0.1 头号问题：A0 = 100%，消融故事已经死了，今天复活它

Day 1 最新全量 run（`a0_20261021_205530`）：**EX（无序）= 100%，EX（有序）= 100%，24/24**。

对照总手册第 0 章的决策表，这落在 "≥ 80% = 题目太 easy" 区间。后果很硬：

- A1/A2/A3/A4 在 EX 上**没有任何提升空间**，Day 5 的消融表会是一条平线，项目核心价值归零。
- 根因不是题不够难，而是 **Chinook 太小**：11 张表、schema 全文约 2–3k token，全量塞进 prompt 又便宜又准确。A1（schema 检索）在这个库上从原理上就不可能赢——没有检索失败的余地，也没有成本压力。

**对策（今天执行，二选一并行）：**

1. **引入第二个、更真实的库（主路）。** 用 Sakila（16 张表，含视图、enum、更绕的 join 路径）新建约 20 道题，难度压在 2–3。Sakila 也不算大，但它的 join 链更长（`payment → customer → address → city → country` 五表链），全 schema 塞 prompt 开始出现"信息稀释"——这是 A1 真正能测量的场景。
2. **修正 A1 的叙事（必须同时做）。** 在小库上，A1 的诚实故事不是"提升 EX"，而是三条：
   - **成本**：每次调用少带多少 token（`avg_in_tokens` 是你今天新增的一等指标）；
   - **可扩展性**：库涨到 100+ 表时全 schema 根本塞不下，检索是唯一出路（在文档里论证，不用真造 100 张表）；
   - **不伤害**：检索不能掉点——如果 A1 的 EX 低于 A0，说明召回漏了 gold 表，这就是"schema 召回率"指标要抓的东西。

> 如果将来想做强对比实验，还可以给 A0/A1 同配换一个弱模型（如本地 qwen2.5:7b），让 headroom 天然出现——"Agent 化在弱模型上收益最大"本身是很好的结论。今天**不做**，记在日报候选里，Day 5 视预算决定。

### 0.2 修日报

打开 `docs/journal/day01.md`，补齐三处：

- `run_id: a0_20261021_205530`；
- headroom 判断：照抄 0.1 的结论，并写清"日报里 95.83% 与最终 100% 的差异"——温度 0 下两次运行仍有一个题翻转，**EX 在 24 题上分母太小，单题波动就是 ±4pt**。这是重要发现：Day 5 全量 150 题前，所有 ±5pt 以内的"提升"都不能当真。写下来，面试能用。
- "Day 2 第一件事"：就是本手册。

### 0.3 修 `truncated` 假阳性 bug（10 分钟）

`src/datapilot/tools/sql_runner.py` 的 `run_sql` 里，变量 `truncated = len(rows) > max_rows` 算对了，但 return 时写的是 `len(rows) >= max_rows`——结果恰好 200 行时会被误标截断。改为：

```python
        truncated = len(rows) > max_rows  # 拿到 max_rows+1 行才说明被截断
        if truncated:
            rows = rows[:max_rows]  # 裁掉多查的那 1 行

        return {
            "ok": True, "error": None, "error_code": None,
            "columns": cols, "rows": rows,
            "truncated": truncated,   # 用上面算好的值，不要重新 len(rows) >= max_rows
            "elapsed_ms": round((time.perf_counter() - t0) * 1000),
        }
```

在 `tests/test_sql_guard.py` 补两个用例，把 bug 钉死：

```python
def test_truncated_flag_exact_boundary():
    # Genre 表恰好 25 行：max_rows=25 时不应误报截断
    r = run_sql(DB, "SELECT * FROM Genre", max_rows=25)
    assert r["ok"] and len(r["rows"]) == 25 and r["truncated"] is False


def test_truncated_flag_when_overflow():
    # Track 3503 行，必然截断
    r = run_sql(DB, "SELECT * FROM Track", max_rows=200)
    assert r["ok"] and len(r["rows"]) == 200 and r["truncated"] is True
```

---

## 1. Day 2 时间表

| 时段 | 任务 | 产出 |
| --- | --- | --- |
| 0:00–1:00 | 第 0 章三笔债 | 日报补齐、bug 修复、单测绿 |
| 1:00–2:00 | schema.py 表级单元化重构（A0 文本逐字节不变） | `tools/schema.py` v2 |
| 2:00–2:40 | gold_tables 自动抽取 + 回填数据集 | `eval/gold_tables.py` |
| 2:40–4:00 | 下载 Sakila + 写 20 题 + verify + 逐条目检 | `data/benchmarks/sakila_v0.jsonl` |
| 4:00–5:30 | BM25 检索器 + FK 一跳扩展 + 单测 | `nodes/schema_retriever.py` |
| 5:30–6:30 | runner 支持 extra 字段 + metrics 加召回率/失败二分 | 小改动 |
| 6:30–7:00 | A1 pipeline + CLI 注册 | `pipelines/a1.py` |
| 7:00–8:00 | 跑 4 组实验：A0/A1 × chinook/sakila | 4 个 run |
| 8:00–8:40 | 对比分析 + 日报 | `docs/journal/day02.md` |

允许超时：Sakila 写题（可从 20 题降到 15 题）。
**不允许超时：检索器单测、"A0 文本不变"的等价性验证。** 公平性是今天全部结论的地基。

---

## 2. 步骤 1：schema.py 表级单元化（60 分钟）

### 2.1 为什么重构

Day 1 的 `full_schema_text()` 吐的是一整块文本。检索器需要的是**表级单元**——每张表一个可独立打分的文档。但有一个铁约束：

> **A0 的 prompt 必须逐字节不变。** 否则 `a0_20261021_205530` 的数字作废，所有对比失去基准。

### 2.2 `src/datapilot/tools/schema.py`（重构后完整版）

```python
# schema 工具的表级单元化版本。
# 约束：full_schema_text() 的输出必须与 Day 1 版本逐字节一致（A0 公平性底线）。

import sqlite3
from pathlib import Path


def connect_ro(db_path: str | Path) -> sqlite3.Connection:
    uri = f"file:{Path(db_path).as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def table_units(db_path: str | Path) -> list[dict]:
    """把 schema 拆成表级单元，每张表一个 dict——检索器的打分对象。"""
    conn = connect_ro(db_path)
    tables = [
        r[0]
        for r in conn.execute(
            "select name from sqlite_master "
            "where type='table' and name not like 'sqlite_%' order by name"
        )
    ]
    units: list[dict] = []
    for t in tables:
        n = conn.execute(f'select count(*) from "{t}"').fetchone()[0]
        cols = [
            {"name": c["name"], "type": c["type"], "pk": bool(c["pk"])}
            for c in conn.execute(f'PRAGMA table_info("{t}")')
        ]
        fks = [
            {"from": fk["from"], "table": fk["table"], "to": fk["to"]}
            for fk in conn.execute(f'PRAGMA foreign_key_list("{t}")')
        ]
        units.append({"table": t, "rows": n, "columns": cols, "fks": fks})
    conn.close()
    return units


def unit_to_text(u: dict) -> str:
    """把单个表单元渲染成与 Day 1 完全相同的文本格式。"""
    lines = [f"TABLE {u['table']}  (rows={u['rows']})"]
    for c in u["columns"]:
        pk = " PRIMARY KEY" if c["pk"] else ""
        lines.append(f"  - {c['name']} {c['type']}{pk}")
    for fk in u["fks"]:
        lines.append(f"  FK: {fk['from']} -> {fk['table']}.{fk['to']}")
    return "\n".join(lines)


def full_schema_text(db_path: str | Path) -> str:
    """与 Day 1 逐字节一致：单元文本 + 每表后一个空行，join 后尾部再去掉一个换行。"""
    units = table_units(db_path)
    return "\n".join(unit_to_text(u) + "\n" for u in units).rstrip("\n")


def schema_text_for(db_path: str | Path, table_names: list[str]) -> str:
    """A1 用：只渲染检索命中的表子集。顺序按表名排序，保证输出确定性。"""
    units = {u["table"]: u for u in table_units(db_path)}
    picked = [units[t] for t in sorted(table_names) if t in units]
    return "\n".join(unit_to_text(u) + "\n" for u in picked).rstrip("\n")


if __name__ == "__main__":
    from datapilot.config import settings
    print(full_schema_text(settings.db_dir / "chinook.db"))
```

### 2.3 等价性验证（写进 tests，不许靠眼睛）

`tests/test_schema.py`：

```python
from pathlib import Path

from datapilot.config import settings
from datapilot.tools.schema import full_schema_text, schema_text_for, table_units

DB = Path(settings.db_dir) / "chinook.db"

# Day 1 输出的前 80 字符快照——重构后必须一致
def test_full_schema_stable_prefix():
    text = full_schema_text(DB)
    assert text.startswith("TABLE Album  (rows=347)\n  - AlbumId INTEGER PRIMARY KEY")
    assert "FK: ArtistId -> Artist.ArtistId" in text
    assert text.count("TABLE ") == 11


def test_units_cover_all_tables():
    units = table_units(DB)
    assert len(units) == 11
    track = next(u for u in units if u["table"] == "Track")
    assert any(c["name"] == "UnitPrice" for c in track["columns"])
    assert any(fk["table"] == "Album" for fk in track["fks"])


def test_subset_rendering():
    text = schema_text_for(DB, ["Track", "Genre"])
    assert "TABLE Track" in text and "TABLE Genre" in text
    assert "TABLE Album" not in text
```

> 注意：快照前缀取自你 Day 1 的实际输出，如果行数/格式不同，以你的真实输出为准改断言。

---

## 3. 步骤 2：gold_tables 自动抽取（40 分钟）

schema 召回率的定义是"gold 用到的表是否都在检索结果里"。gold 表**不要手标**——从 `gold_sql` 里用 sqlglot 解析出来，零人工成本且不会标错。

`src/datapilot/eval/gold_tables.py`：

```python
# 从 gold_sql 解析引用表名，回填到数据集的 gold_tables 字段。
# 关键细节：CTE 别名会被 sqlglot 当成 Table 节点，必须排除。

import json
from pathlib import Path

import sqlglot
from sqlglot import exp


def extract_tables(sql: str) -> list[str]:
    tree = sqlglot.parse_one(sql, read="sqlite")
    cte_aliases = {c.alias for c in tree.find_all(exp.CTE)}
    return sorted(
        {t.name for t in tree.find_all(exp.Table) if t.name not in cte_aliases}
    )


def backfill(dataset_path: str | Path) -> dict:
    ds = Path(dataset_path)
    items = [json.loads(l) for l in ds.read_text(encoding="utf-8").splitlines() if l.strip()]
    n = 0
    for it in items:
        if it.get("gold_sql"):
            it["gold_tables"] = extract_tables(it["gold_sql"])
            n += 1
    ds.write_text(
        "\n".join(json.dumps(x, ensure_ascii=False) for x in items),
        encoding="utf-8",
    )
    return {"backfilled": n, "total": len(items)}


if __name__ == "__main__":
    from datapilot.config import settings
    print(backfill(settings.dataset))
```

`tests/test_gold_tables.py`：

```python
from datapilot.eval.gold_tables import extract_tables


def test_simple_join():
    sql = "SELECT * FROM Track t JOIN Genre g ON t.GenreId = g.GenreId"
    assert extract_tables(sql) == ["Genre", "Track"]


def test_cte_alias_excluded():
    sql = "WITH x AS (SELECT GenreId FROM Track) SELECT * FROM x JOIN Genre USING (GenreId)"
    assert extract_tables(sql) == ["Genre", "Track"]  # x 是 CTE 别名，不是表


def test_subquery():
    sql = "SELECT * FROM Customer WHERE CustomerId IN (SELECT CustomerId FROM Invoice)"
    assert extract_tables(sql) == ["Customer", "Invoice"]
```

跑 `python -m src.datapilot.eval.gold_tables` 回填 chinook_v0.jsonl，然后**抽查 3 题**确认 gold_tables 正确。

---

## 4. 步骤 3：Sakila + 20 道新题（80 分钟上限，可砍到 15 题）

### 4.1 拿库

```powershell
cd D:\download\AI\ChatGPT\Work\agent-project-1\datapilot
curl.exe -L -o data\dbs\sakila.db "https://github.com/bradleygrant/sakila-sqlite3/raw/main/sakila.db"

# 代理
curl.exe -L --proxy http://127.0.0.1:10808 -o data\dbs\sakila.db "https://github.com/bradleygrant/sakila-sqlite3/raw/main/sakila.db"
```

验证后**先把 schema 打出来看**：

```powershell
python -m src.datapilot.tools.schema  # 或写三行脚本对 sakila.db 调 full_schema_text
```

两件事必须确认（不同移植版差异很大，别信任何教程的字段名）：
1. 表名大小写（有的版本是 `film`，有的是 `Film`）；
2. `film.rating` 是 TEXT 还是别的类型、`payment`/`rental` 是否存在。

**如果 40 分钟还没拿到可用库，放弃 Sakila**，退回备选：把 Chinook 的题扩 15 道难度 3 的 nested/HAVING 题，今天照常做检索器（叙事只剩"成本"一条，弱了，但项目不死）。数据获取不值得烧半天。

### 4.2 出题

分布（20 题）：simple 4 / aggregation 5 / join 5 / nested 4 / ambiguous 1 / adversarial 1。其中 **8 道中文题**。难度压 2–3，别再出难度 1 的送分题——Sakila 的任务就是制造 headroom。

三道写好的样例（字段名以你实际 schema 为准，verify 后逐条目检）：

```jsonl
{"id": "sa-001", "db_id": "sakila", "question": "评级为 PG-13 的电影有多少部？", "question_type": "simple", "difficulty": 1, "gold_sql": "SELECT COUNT(*) FROM film WHERE rating = 'PG-13';", "gold_result": null, "expected_behavior": "answer", "ambiguous": false, "order_sensitive": false, "notes": "单表过滤；确认 rating 列取值形式"}
{"id": "sa-002", "db_id": "sakila", "question": "每个国家客户的支付总额，取前 5 名。金额相同按国家名升序。", "question_type": "join", "difficulty": 3, "gold_sql": "SELECT co.country, SUM(p.amount) FROM payment p JOIN customer c ON p.customer_id = c.customer_id JOIN address a ON c.address_id = a.address_id JOIN city ci ON a.city_id = ci.city_id JOIN country co ON ci.country_id = co.country_id GROUP BY co.country ORDER BY 2 DESC, co.country LIMIT 5;", "gold_result": null, "expected_behavior": "answer", "ambiguous": false, "order_sensitive": true, "notes": "五表链 join；正是为了考 schema 检索与长链 join"}
{"id": "sa-003", "db_id": "sakila", "question": "租借次数超过其所属类别平均租借次数的电影，返回电影标题。", "question_type": "nested", "difficulty": 3, "gold_sql": "SELECT f.title FROM film f JOIN film_category fc ON f.film_id = fc.film_id JOIN (SELECT fc2.category_id, AVG(cnt) AS avg_cnt FROM (SELECT fc2.category_id, i.film_id, COUNT(r.rental_id) AS cnt FROM film_category fc2 JOIN inventory i ON fc2.film_id = i.film_id JOIN rental r ON i.inventory_id = r.inventory_id GROUP BY fc2.category_id, i.film_id) t JOIN film_category fc2 ON 1=0 WHERE 1=0) x ON 1=0 GROUP BY f.film_id;", "gold_result": null, "expected_behavior": "answer", "ambiguous": false, "order_sensitive": false, "notes": "【占位骨架——这条 SQL 是故意写残的，你必须自己写出正确版本】类别平均需要两层聚合"}
```

> sa-003 我故意留了一条写残的 SQL。原因：这道题是全套题里最能区分"会不会写两层聚合"的题，你的 gold 必须自己写、自己跑、自己目检——照抄我的等于白做。写不出来就换成一道你会写的难度 3 题，不丢人，造假才丢人。

写完照例：

```powershell
python -m src.datapilot.cli verify-gold --dataset data/benchmarks/sakila_v0.jsonl
python -m src.datapilot.eval.gold_tables  # 改一下脚本支持传参，或手动调用 backfill
```

然后**逐条目检 gold_result**。Sakila 数据量比 Chinook 大，特别检查 0 行和接近 200 行的。

---

## 5. 步骤 4：BM25 检索器 + FK 一跳扩展（90 分钟，今天的主菜）

### 5.1 设计决策（先想清楚再写）

- **为什么 BM25 打底而不是直接上向量**：零外部依赖、零额外 API 成本、结果确定可复现（评测纪律）、对"表名/列名精确词"（GenreId、rating）的匹配比向量更稳。向量版是今天的 bonus，不是必需品——DeepSeek 没有 embedding API，阿里云有 `text-embedding-v4`，有 key 再做，没有就在文档里诚实写"向量检索留作后续工作"。
- **中英文混合分词**：表名列名是英文，问题是中文。英文按标识符切词（`GenreId → genreid`，可做驼峰/下划线二次切分），中文按字 + 二元组。不引入 jieba——为一个检索器多一个重依赖不值。
- **文档内容**：`表名 + 列名 + 外键文本 + 前 3 行采样值`。采样值让"巴西/PG-13"这类字面量也能命中表。采样必须走 `run_sql`（有守卫），别绕过自己的安全层。
- **FK 一跳扩展**：BM25 top-k 之后，把命中表的外键邻居（双向）全部补进来。理由：join 题的中间表（如 `PlaylistTrack`、`film_category`）在问题里往往一个字不提，纯文本匹配永远召不回它们。**这一跳就是 A1 相对朴素检索的增量，也是面试可讲点。**

### 5.2 `src/datapilot/nodes/schema_retriever.py`

```python
# schema 检索器：BM25 打分 + 外键图一跳扩展。
# 确定性设计：同问题、同库，输出必须完全一致（评测可复现的纪律）。

from __future__ import annotations

import re
from pathlib import Path

from rank_bm25 import BM25Okapi

from datapilot.tools.schema import table_units
from datapilot.tools.sql_runner import sample_rows


def tokenize(text: str) -> list[str]:
    """英文标识符（含驼峰/下划线二次切分）+ 中文单字与二元组。"""
    text = text.lower()
    toks: list[str] = []
    for word in re.findall(r"[a-z_][a-z0-9_]*", text):
        toks.append(word)
        toks.extend(re.findall(r"[a-z]+", word))  # 拆下划线
    # 驼峰切分要在小写化之前做，这里退而求其次：原词已入库，靠中文二元组兜底
    zh = re.findall(r"[一-鿿]", text)
    toks.extend(zh)
    toks.extend("".join(p) for p in zip(zh, zh[1:]))
    return toks


class SchemaRetriever:
    def __init__(self, db_path: str | Path, sample_n: int = 3):
        self.db_path = Path(db_path)
        self.units = table_units(self.db_path)
        self.docs: list[str] = []
        for u in self.units:
            col_names = " ".join(c["name"] for c in u["columns"])
            fk_text = " ".join(f"{fk['from']} {fk['table']} {fk['to']}" for fk in u["fks"])
            samples = sample_rows(self.db_path, u["table"], n=sample_n)
            sample_text = " ".join(str(v) for row in samples for v in row)
            self.docs.append(f"{u['table']} {col_names} {fk_text} {sample_text}")
        self.bm25 = BM25Okapi([tokenize(d) for d in self.docs])

        # 外键邻接表（双向）
        self.neighbors: dict[str, set[str]] = {u["table"]: set() for u in self.units}
        for u in self.units:
            for fk in u["fks"]:
                self.neighbors[u["table"]].add(fk["table"])
                if fk["table"] in self.neighbors:
                    self.neighbors[fk["table"]].add(u["table"])

    def retrieve(self, question: str, top_k: int = 4, expand_fk: bool = True) -> list[str]:
        """返回表名列表，排序确定（分数降序，平分按表名字典序）。"""
        scores = self.bm25.get_scores(tokenize(question))
        ranked = sorted(
            zip((u["table"] for u in self.units), scores),
            key=lambda x: (-x[1], x[0]),
        )
        hit = {t for t, s in ranked[:top_k] if s > 0}
        if not hit:  # 全零分时保底取 top_k，宁可多给不能漏
            hit = {t for t, _ in ranked[:top_k]}
        if expand_fk:
            hit = hit | {nb for t in hit for nb in self.neighbors.get(t, ())}
        return sorted(hit)


if __name__ == "__main__":
    from datapilot.config import settings
    r = SchemaRetriever(settings.db_dir / "chinook.db")
    for q in ["每个音乐流派的曲目数量", "客户 Nancy 的邮箱", "哪些影片被租借次数最多"]:
        print(q, "->", r.retrieve(q))
```

装依赖：`uv add rank-bm25`

### 5.3 `tests/test_retriever.py`

```python
from pathlib import Path

from datapilot.config import settings
from datapilot.nodes.schema_retriever import SchemaRetriever, tokenize

DB = Path(settings.db_dir) / "chinook.db"


def test_tokenize_mixed():
    toks = tokenize("查询 GenreId 对应的流派")
    assert "genreid" in toks and "流派" in toks


def test_direct_hit():
    r = SchemaRetriever(DB)
    got = r.retrieve("客户 Nancy 的邮箱是什么？")
    assert "Customer" in got


def test_fk_expansion_brings_join_table():
    r = SchemaRetriever(DB)
    # "播放列表里有某曲目"命中 Playlist/Track，一跳应补进 PlaylistTrack
    got = r.retrieve("播放列表 Music 里有哪些曲目？")
    assert "PlaylistTrack" in got


def test_determinism():
    r = SchemaRetriever(DB)
    assert r.retrieve("每个国家的客户数") == r.retrieve("每个国家的客户数")
```

`test_fk_expansion` 如果挂了，先打印 `retrieve` 的中间结果再调 top_k——**不许为了让测试变绿而删掉断言**。

---

## 6. 步骤 5：runner 与 metrics 的小改动（40 分钟）

### 6.1 runner 支持 extra 透传 + 召回率计算

`src/datapilot/eval/runner.py` 的 `score_one` 里，在 return 的 dict 前加：

```python
    # 召回率：仅 answer 题、且 pipeline 上报了检索结果时有意义
    extra = dict(out.get("extra") or {})
    if (
        q["expected_behavior"] == "answer"
        and out.get("retrieved_tables") is not None
        and q.get("gold_tables")
    ):
        extra["schema_recall"] = int(
            set(q["gold_tables"]) <= set(out["retrieved_tables"])
        )
```

并在 return 的 dict 里加两个字段（保持向后兼容，旧 results.jsonl 没有这两个键，aggregate 用 `.get` 不会炸）：

```python
        "gold_tables": q.get("gold_tables"),
        "retrieved_tables": out.get("retrieved_tables"),
        **extra,
```

### 6.2 metrics 加两个聚合

`src/datapilot/eval/metrics.py` 的 `aggregate` return dict 里加：

```python
        # schema 召回率（A1 类 run 才有；None 表示该 run 无检索）
        "schema_recall": (
            lambda xs: round(sum(xs) / len(xs), 4) if xs else None
        )([r["schema_recall"] for r in answerable if r.get("schema_recall") is not None]),
        # 平均输入 token（成本的直接解释变量；A0 的 extra 里不放，向后兼容为 None）
        "avg_in_tokens": (
            lambda xs: round(sum(xs) / len(xs)) if xs else None
        )([r["in_tokens"] for r in records if r.get("in_tokens")]),
```

再加一个失败二分函数——这是 A1 对比分析的核心：

```python
def failure_split(records: list[dict]) -> dict:
    """把 ex=False 的题分成两类：检索没召回 gold 表（retrieval）vs 召回了但生成错（generation）。
    只有带 retrieved_tables 的 run 才有意义。A0 的全错都该算 generation。"""
    retr = gen = 0
    for r in records:
        if r.get("ex") is not False or not r.get("gold_tables"):
            continue
        rt = r.get("retrieved_tables")
        if rt is None:
            gen += 1
        elif set(r["gold_tables"]) <= set(rt):
            gen += 1
        else:
            retr += 1
    return {"retrieval_errors": retr, "generation_errors": gen}
```

### 6.3 report.py 的汇总表加两行

在 `write_report` 的汇总表里，EX 行后面加（注意 None 的处理）：

```python
        f"| Schema 召回率 | {('%' + format(summary['schema_recall'], '.2%')) if summary.get('schema_recall') is not None else 'N/A'} |",
        f"| 平均输入 token | {summary.get('avg_in_tokens') or 'N/A'} |",
```

> 上面那行 f-string 嵌套容易写错，写错就拆成两行普通代码，别在格式化上炫技。

---

## 7. 步骤 6：A1 pipeline（30 分钟）

`src/datapilot/pipelines/a1.py`：

```python
# A1 = A0 + schema 检索。其余一切（SYSTEM、模型、温度、JSON 格式）与 A0 完全一致。
# 公平性底线：A0 与 A1 的唯一差异是"喂给模型的 schema 文本从全量变成检索子集"。

from __future__ import annotations

from datapilot.config import settings
from datapilot.llm.client import LLMClient
from datapilot.nodes.schema_retriever import SchemaRetriever
from datapilot.pipelines.a0 import SYSTEM, extract_json  # 直接复用，禁止复制粘贴后改字
from datapilot.tools.schema import schema_text_for
from datapilot.tools.sql_runner import run_sql

_retrievers: dict[str, SchemaRetriever] = {}


def get_retriever(db_id: str) -> SchemaRetriever:
    if db_id not in _retrievers:
        _retrievers[db_id] = SchemaRetriever(settings.db_dir / f"{db_id}.db")
    return _retrievers[db_id]


def a1_answer(q: dict, client: LLMClient | None = None, top_k: int = 4) -> dict:
    client = client or LLMClient()
    retriever = get_retriever(q["db_id"])
    tables = retriever.retrieve(q["question"], top_k=top_k)
    schema = schema_text_for(settings.db_dir / f"{q['db_id']}.db", tables)
    user = f"# 数据库 Schema（检索子集）\n{schema}\n\n# 用户问题\n{q['question']}"

    r = client.chat_json(SYSTEM, user)
    try:
        payload = extract_json(r.text)
    except Exception as e:
        return {
            "status": "parse_error", "sql": None, "rows": None,
            "error": f"parse_error: {e}", "behavior": "answer",
            "llm_calls": 1, "cost_cny": r.cost_cny,
            "retrieved_tables": tables,
            "extra": {"in_tokens": r.in_tokens, "schema_chars": len(schema)},
        }

    sql = payload.get("sql", "")
    res = run_sql(
        settings.db_dir / f"{q['db_id']}.db", sql,
        max_rows=settings.max_rows, timeout_s=settings.sql_timeout_s,
    )
    return {
        "status": "ok" if res["ok"] else "sql_error",
        "sql": sql,
        "tables_used": payload.get("tables_used"),
        "assumptions": payload.get("assumptions"),
        "rows": res["rows"] if res["ok"] else None,
        "columns": res["columns"],
        "error": None if res["ok"] else res["error"],
        "error_code": res.get("error_code"),
        "behavior": "answer",
        "llm_calls": 1,
        "cost_cny": r.cost_cny,
        "retrieved_tables": tables,
        "extra": {"in_tokens": r.in_tokens, "schema_chars": len(schema)},
    }
```

`cli.py` 的 `get_pipeline` 注册：

```python
    if name == "a1":
        from datapilot.pipelines.a1 import a1_answer
        return a1_answer
```

> 注意一个已知的不完美：prompt 指纹哈希的是 `a0.SYSTEM`，A1 复用同一 SYSTEM，指纹相同——这是**特性不是 bug**，它声明"A0 与 A1 的生成提示词完全一致，唯一变量是 schema 内容"。但 schema 内容不同没被指纹覆盖，这个局限写进日报"已知局限"里，Day 5 可以再补 schema 指纹。

---

## 8. 步骤 7：跑 4 组实验（60 分钟，大部分是等）

```powershell
# A1 先冒烟 3 题，确认检索子集合理、成本下降
python -m src.datapilot.cli eval --config a1 --limit 3 --run-id a1_smoke

# 正式 4 组（顺序执行，别并发——限流）
python -m src.datapilot.cli eval --config a1 --run-id a1_chinook
python -m src.datapilot.cli eval --config a0 --dataset data/benchmarks/sakila_v0.jsonl --run-id a0_sakila
python -m src.datapilot.cli eval --config a1 --dataset data/benchmarks/sakila_v0.jsonl --run-id a1_sakila
```

> chinook 的 A0 用已有 run（`a0_20261021_205530`），别重跑——省的钱和保证的可比性都是你的。

跑完填这张表（写进日报）：

| run | 数据集 | EX | schema 召回率 | avg_in_tokens | 单题成本 | 检索错 / 生成错 |
| --- | --- | --- | --- | --- | --- | --- |
| A0 | chinook(30) | 1.000 | N/A | ? | ? | 0 / 0 |
| A1 | chinook(30) | ? | ? | ? | ? | ? / ? |
| A0 | sakila(20) | ? | N/A | ? | ? | - / ? |
| A1 | sakila(20) | ? | ? | ? | ? | ? / ? |

**解读规则（先记住，数字出来对号入座）：**

- A1(chinook) EX < 100% → 检索在小库上反而漏表，看召回率是不是 < 1，是的话调 top_k（4→6）重跑一次，记录"top_k 敏感性"这本身就是发现。
- A0(sakila) EX 明显低于 100% → headroom 出现了，Sakila 引入成功，Day 3 的修复环有空间可涨。
- A0(sakila) ≈ A1(sakila) 且召回率 100% → 正常且诚实的结果：检索不伤点、省了 token。把这个写成结论，不要硬造差异。
- 失败题全部落在"生成错" → 好消息：说明瓶颈在生成，正好是 Day 3 修复环的靶子。

---

## 9. Day 2 日报模板

写到 `docs/journal/day02.md`：

```markdown
# Day 2

## 目标完成度
- [ ] 日报三笔债（headroom 判断 / run_id / 两个数字差异的解释）
- [ ] truncated bug 修复 + 单测
- [ ] schema 表级单元化（A0 文本不变，有等价性测试）
- [ ] gold_tables 自动回填
- [ ] Sakila + 20 题（目检完成）
- [ ] BM25 + FK 一跳检索器（单测绿）
- [ ] 4 组 run 完成，对比表填写

## 对比表
（贴 8.0 的表）

## 三个结论（必须有，哪怕是负结果）
1. A1 相对 A0 的 EX 变化是……，归因于……
2. 输入 token 从 X 降到 Y，单题成本从 ……
3. 失败二分：检索错 n=?, 生成错 n=?，说明瓶颈在……

## 已知局限（写给自己，面试时用）
- prompt 指纹不覆盖 schema 内容差异
- top_k=4 是拍的，只做了粗敏感性检查
- BM25 对中文业务词（如"消费额"→Total）无语义映射能力，这是向量/词典版的改进空间

## 明天（Day 3）第一件事
把 A1 的 pipeline_fn 换成 LangGraph 图执行函数，runner 一行不改——验证 Day 1 的接口约定真的兑现了。
```

---

## 10. Day 2 验收清单

- [ ] `pytest -q` 全绿（含 truncated 边界、schema 等价性、检索器确定性、gold_tables 抽取）
- [ ] `full_schema_text` 输出与 Day 1 一致（有测试钉住）
- [ ] chinook_v0.jsonl 和 sakila_v0.jsonl 的 answer 题都有 `gold_result` 和 `gold_tables`，且我逐条看过
- [ ] A1 的 SYSTEM 是 `from a0 import SYSTEM`，不是复制粘贴
- [ ] 4 个 run 目录里都有 meta.json / results.jsonl / report.md
- [ ] 日报有对比表和至少一条负结果或意外发现
- [ ] 能说清：为什么 FK 一跳扩展是必要的（用 PlaylistTrack / film_category 举例）

---

## 11. 五个会让你今天翻车的坑

1. **重构 schema.py 时顺手"优化"输出格式。** A0 文本一变，昨天的数字全废。先写等价性测试再动手。
2. **检索器采样绕过 run_sql。** 自己写 `conn.execute(f"SELECT * FROM {t}")` 一时爽，安全层被架空，后面所有工具都开始各写一套。
3. **为了召回率把 top_k 调到天大。** top_k=11 等于回到 A0。检索的意义是"少而准"，召回率 100% 且 schema_chars 明显下降才是赢。
4. **Sakila 字段名想当然。** 先打 schema 再写题，verify-gold 报错不是麻烦，是在救你。
5. **A1 掉了点就偷偷改 A1 的 prompt。** 这是作弊——消融的每个格子只能有一个变量。掉点是数据，不是耻辱。

---

## 12. 明天的接口约定（Day 3 直接接）

| 今天的产物 | Day 3 怎么用 |
| --- | --- |
| `SchemaRetriever.retrieve(question, top_k) -> list[str]` | `schema_retriever` 节点直接调，结果写进 `AgentState.schema_subset` |
| `score_one(q, pipeline_fn)` | pipeline_fn 换成图执行函数 `graph_answer(q)`，返回字段对齐即可，runner 零改动 |
| `retrieved_tables` / `schema_recall` 字段 | Day 3 起所有配置都带检索，失败二分成为标准分析动作 |
| `extra` 透传机制 | Day 3  diagnoser 的错误分类、attempts 数都走 extra 进记录 |

最后一句：今天最重要的产出不是检索器，是**那张 4 格对比表和"Sakila 上 A0 到底多少分"这个答案**。它决定 Day 3–5 的故事是"修复环带来 +X pt"还是"所有配置都是 100%，项目需要紧急转向"。跑出数字再睡觉。
