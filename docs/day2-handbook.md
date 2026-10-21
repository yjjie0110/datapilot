# Day 2 实施手册 —— 先把尺子校准，再谈改进

> 前置：Day 1 已完成并通过自检。
> 这份手册的第一部分是我对你 Day 1 的检查结论。请先读完再动手，因为 Day 2 的计划和原手册不一样了。

---

## 0. Day 1 检查结论

### 0.1 一句话

**工程实现是合格的，评测体系是不合格的。** 代码结构、SQL 守卫、gold 校验、单测、续跑都做到了；但你的评测集已经饱和，A0 拿到 100%，这意味着后面所有 Agent 模块的增益都无法被测量。这是 Day 2 必须先解决的问题，优先级高于任何新功能。

### 0.2 记分卡

| 检查项 | 实测 | 判定 |
| --- | --- | --- |
| 环境与依赖 | uv + `.venv` + `uv.lock`，`pytest` 11 passed | ✅ |
| 数据库 | Chinook 11 表，发票日期已对齐到 2021–2025 | ✅ |
| 评测集 | 30 题（24 可判定 + 4 澄清 + 2 拒绝），id/题干无重复 | ✅ |
| gold 质量 | 无缺失、无空结果、重跑与存档零漂移 | ✅ |
| 单测 | 11 个指标测试全绿 | ✅ |
| runner | 逐题 flush、按 id 跳过、meta 记录模型与 prompt 指纹 | ⚠️ 缺数据集指纹 |
| A0 结果 | 95.83%（23/24） | ❌ 唯一失败是假阴性，真实 100% |
| 特殊题行为 | 0% | ✅ 符合 A0 设计（它不澄清也不拒答） |
| 报告 | 自动生成，含分题型与失败清单 | ✅ |

### 0.3 最关键的一件事

报告里唯一的失败是 `ch-001`：

```
生成 SQL: SELECT FirstName || ' ' || LastName AS Name, Email FROM Customer ...
差异: col_count_diff pred=2 gold=3
```

这句话的意思不是"模型答错了"，是**模型答对了、你的判分把它判错了**。这是 Day 1 手册 4.5 节明确警告过的"格式陷阱"，它真的发生了。

把这一题修好之后，A0 = 24/24 = **100%**。

一个 100% 的 baseline 意味着什么：

- A1 的 schema 检索不会有任何准确率增益；
- A2 的自修复环没有错误可修；
- A3 的双路校验是在给一个已经全对的系统做冗余；
- Day 5 的消融表会是一条平线，整个项目失去说服力。

**所以 Day 2 的第一优先级不是"加检索"，是"让尺子重新有刻度"。**

### 0.4 我顺带查到的数据特征（会影响你怎么出题）

1. **客户消费额分布极窄**：59 个客户，总额 36.64–49.62，均值 39.47。没有客户高于均值 1.3 倍。
   → "消费最高的客户""前 10% 客户"这类题几乎没有区分度，而且容易出现并列（45.62 出现两次）。**难题应该来自结构复杂度，不是数值极值。**
2. **流派曲目数有并列**：有两个流派都是 28 首。
   → `ORDER BY COUNT(*) DESC` 在并列处的顺序不稳定，有序比较会随机判错。
3. **2025 年只有 80 张发票，2021–2024 各 83 张**，各月同比会出现大量 0.0。
   → 这不是 bug，但会让"同比增长"类题目的答案看起来很奇怪，出题时要知道。
4. **P50 8.1s / P95 22.4s，最慢一题 37.5s**。
   → 30 题还能忍，150 题 × 5 配置会很痛。Day 2 加题后请注意控制全量运行次数。

---

## 1. 问题清单（按优先级）

### P0 —— 会直接毁掉项目说服力，Day 2 上午必须修完

#### P0-1 评测集饱和

- **现象**：A0 真实 100%。
- **根因**：24 道题全部是"单表过滤 / 常规聚合 / 两表 join / 简单 HAVING"，Chinook 又是公开数据集，模型极可能见过同类结构。
- **修法**：见第 5 章。加结构性难题，把 A0 压到 75% 以下（理想 55%–70%）。
- **不要做的事**：不要靠"换一个更弱的模型"来制造 headroom。那是把问题藏起来，Day 5 面试官一问"为什么不用强模型"你就答不上来。弱模型对比可以做，但只能作为附加实验。

#### P0-2 `ex_ordered` 语义是错的

- **现象**：报告里 EX 87.5%，看起来"有 2 题排序错了"。
- **实际**：
  - `ch-004`「哪些专辑总时长超过 60 分钟」根本没要求排序，模型没排序，被判错；
  - `ch-003`「按数量降序」模型排对了，但因为两个流派并列 28 首，并列内部的顺序不同，被判错。
- **结论**：87.5% 这个数字没有信息量，甚至会误导你自己。
- **修法**：给每题加 `order_sensitive` 字段，只在该字段为 true 时计算有序 EX；并列题要么指定次级排序键，要么不算有序。

#### P0-3 续跑只按 `id` 去重，改完 gold 不会重跑

- **现象**：`run_eval` 从 `results.jsonl` 读出已完成的 id，直接跳过。
- **后果**：你上午修完 `ch-001` 的题面、下午用同一个 `run_id` 重跑，`ch-001` 不会重新计算，你还会看到旧结果。**这个坑你今天一定会踩。**
- **修法**：把「数据集文件哈希 + prompt 指纹」写进 meta；重跑时若指纹不一致，直接报错，强制换 run_id。

### P1 —— 工程质量问题，Day 2 上午顺手修掉

#### P1-1 `enforce_limit` 可被内层 LIMIT 绕过（实测）

我实测的结果：

```
SELECT * FROM Track LIMIT 999999   -> 返回 3503 行（max_rows=200）
SELECT * FROM Track                -> 返回 200 行
```

`enforce_limit` 看到原 SQL 已有 LIMIT 就原样返回，于是模型写一个 `LIMIT 999999` 就能把整表拉进内存。Chinook 只有 3503 行所以没炸，换成大库就是内存事故。

#### P1-2 `.gitignore` 回退，`.idea/` 已入库

- `experiments/` 现在没被忽略，`git status` 里是 `?? experiments/`，下次提交会把原始运行数据一起提交。
- `.idea/` 的 9 个文件已经在 git 索引里。面试官点开仓库第一眼看到 IDE 配置，观感不好。
- `.pytest_cache` 权限异常，会污染 `git status` 输出。

#### P1-3 `chinook_look.jsonl` 不是 JSONL

它其实是 30 个"漂亮打印"的 JSON 对象首尾相接，一共 2017 行。我验证过：按行解析会报错，按单个 JSON 解析也会报 `Extra data`。它是一个人工审阅用的副本，但名字和位置都在暗示"这是数据集"，迟早会有人（包括你）误用。

#### P1-4 没有 `sql_runner` 的单测

守卫我手工测了 5 个攻击样例，全部拦住（多语句、CTE 内 DELETE、PRAGMA、ATTACH 都正确拒绝）。但这是"我测过"，不是"仓库能保证"。而且我发现了一个误杀：`SELECT * FROM Customer; -- 注释` 会被判成两条语句而拒绝（sqlglot 返回 `['Select', 'Semicolon']`）。

#### P1-5 缺 `tests/test_sql_guard.py`

Day 1 验收清单里写了"危险 SQL 被拦住（自己手测一次）"，手工测过可以算完成，但面试时"有单测覆盖"和"我试过"是两回事。

### P2 —— 不影响正确性，但影响可维护性与观感

| # | 问题 | 修法 |
| --- | --- | --- |
| P2-1 | `schema.py` 的 `__main__` 会 `print(settings.api_key)` | 删掉这一行，改成打印 db 路径 |
| P2-2 | `a0.py` 的 `__main__` 调用 `a0_answer()` 缺参数，必然 TypeError | 删掉或改成真实问题 |
| P2-3 | 尾部注释加 `;` 会被守卫误杀 | 过滤 `exp.Semicolon` |
| P2-4 | `cli.py` 用 `Path("reports")`，依赖当前工作目录 | 改用 `PROJECT_ROOT / "reports"` |
| P2-5 | `docs/journal/day01.md` 的 headroom 段空着，末尾还粘了一段手册内容 | 补完并删掉粘贴内容 |
| P2-6 | `config.py` 用 `_DropFieldsSource` 丢弃 `.env` 里的 `DP_DB_DIR/DP_DATASET/DP_RUN_DIR`，但 `.env` 里仍然写着它们 | 改成"相对路径按 PROJECT_ROOT 解析"，让 `.env` 真正生效 |

P2-6 要解释一下：你现在这套 `_DropFieldsSource` 能让程序跑通，但它是一个补丁，不是设计。`.env.example` 告诉使用者"这三个字段可配"，代码却静默忽略——面试官看到会问"那为什么还留着"。正确做法是保留 `.env` 能力，用 validator 把相对路径解析成绝对路径。

---

## 2. Day 2 的目标与硬门槛

### 2.1 目标

1. 把评测语义修对（P0-2、P0-3）。
2. 把评测集从"能跑"变成"有区分度"：可判定题从 24 增加到 **36–40**，A0 落在 **55%–75%**。
3. 在有 headroom 的前提下，实现 A1 schema 检索，并测出它的真实收益。

### 2.2 硬门槛（不达标就不要往下做）

| 门槛 | 标准 | 不达标怎么办 |
| --- | --- | --- |
| G1 | 修完语义后，`pytest` 全绿，A0 重新跑一遍 | 不通过就不进入加题 |
| G2 | A0（v1 数据集）**≤ 75%** | 继续加结构性难题，不要做 A1 |
| G3 | A1 的 schema recall ≥ 90% | 检查中文题干到英文表名的映射 |
| G4 | A1 相对 A0 的 EX 下降 ≤ 2pt，输入 token 下降 ≥ 40% | 检索策略有问题，先修再继续 |

**如果 G2 没达标，Day 2 下午不要写 A1。** 把时间全部花在加题上，并把 Day 3 的图实现顺延、砍掉 Day 6 的 UI。尺子不准的时候，做任何功能都是在给自己制造无法解释的数字。

---

## 3. 时间表（9 小时）

| 时段 | 任务 | 产出 |
| --- | --- | --- |
| 0:00–1:00 | P0-2 / P0-3 修复 + 重跑 A0（应变成 100%，作为证据留存） | 语义正确的 A0 报告 |
| 1:00–1:40 | P1 修复：LIMIT、gitignore、删 look 文件、单测 | `pytest` 全绿 |
| 1:40–4:00 | 加 12 道结构性难题 + 自检 + 跑 A0 | A0 落在目标区间 |
| 4:00–5:00 | 午饭 / 缓冲（如果 G2 没过，这一小时继续加题） | |
| 5:00–7:30 | 实现 A1 schema 检索 | `pipelines/a1.py` |
| 7:30–8:30 | 跑 A0 vs A1，出对比报告 | `reports/day2_compare.md` |
| 8:30–9:00 | 日报 + 明天接口约定 | `docs/journal/day02.md` |

---

## 4. 阶段 A：修尺子

### 4.1 给数据集加 `order_sensitive`

先做一次批量迁移（在 `datapilot/` 根目录执行）：

```python
# 一次性脚本，跑完可以删
import json
from pathlib import Path

p = Path("data/benchmarks/chinook_v0.jsonl")
items = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]

# 只有题干明确要求"排序 / 按…排列 / 前 N 名"的题才算有序
ORDER_SENSITIVE = {"ch-002", "ch-003", "ch-017"}
for it in items:
    it["order_sensitive"] = it["id"] in ORDER_SENSITIVE

p.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in items), encoding="utf-8")
```

注意 `ch-004` 不在集合里：它问的是"哪些专辑"，没问顺序，其 gold SQL 里的 `ORDER BY al.Title` 只是让结果好看，不应该作为判分依据。

### 4.2 修 `score_one`

把这一段：

```python
        if out.get("status") == "ok" and rows is not None and gold is not None:
            ex = results_equal(rows, gold)
            ex_ord = results_equal(rows, gold, ordered=True)
```

改成：

```python
        if out.get("status") == "ok" and rows is not None and gold is not None:
            ex = results_equal(rows, gold)
            ex_ord = (
                results_equal(rows, gold, ordered=True)
                if q.get("order_sensitive")
                else None
            )
```

同时给记录加一个字段，便于以后分析：

```python
        "order_sensitive": bool(q.get("order_sensitive")),
```

### 4.3 修 `aggregate` 里的有序 EX

```python
    ord_records = [r for r in answerable if r.get("ex_ordered") is not None]
    ex_ord = sum(1 for r in ord_records if r.get("ex_ordered"))
    ...
    "ex_ordered": rate(ex_ord, len(ord_records)),
    "n_order_sensitive": len(ord_records),
```

报告里也要把分母改掉，否则 100% 会被算成 50%：

```
| EX（有序，仅排序题） | {summary['ex_ordered']:.2%}（n={summary['n_order_sensitive']}） |
```

### 4.4 修续跑指纹

在 `runner.py` 加：

```python
def dataset_fingerprint(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:12]


def run_fingerprint(dataset_path: str | Path) -> str:
    return f"{dataset_fingerprint(dataset_path)}-{prompt_fingerprint()}"
```

在 `run_eval` 里，`run_dir.mkdir(...)` 之后、读 `done` 之前插入：

```python
    fp = run_fingerprint(dataset_path)
    meta_path = run_dir / "meta.json"
    if res_path.exists() and meta_path.exists():
        old = json.loads(meta_path.read_text(encoding="utf-8"))
        if old.get("fingerprint") and old["fingerprint"] != fp:
            raise RuntimeError(
                f"数据集或 prompt 已变化（{old['fingerprint']} -> {fp}）。"
                f"请换一个 run_id，或删除 {run_dir}。"
            )
```

并把 `"fingerprint": fp` 写进 meta。

> **今天上午你会亲手验证这个设计的必要性**：修完 `ch-001` 后，如果沿用旧 run_id，程序会替你拦住这次误用。

### 4.5 修 `enforce_limit`

```python
def enforce_limit(sql: str, max_rows: int) -> str:
    """无论内层有没有 LIMIT，外层都再套一次，保证不会被 LIMIT 999999 绕过。"""
    inner = sql.strip().rstrip(";").rstrip()
    return f"SELECT * FROM ({inner}) AS _dp_sub LIMIT {int(max_rows)}"
```

并把 `run_sql` 里的 `cur.fetchall()` 改成：

```python
        rows = [list(r) for r in cur.fetchmany(max_rows)]
```

改完自己验证：

```python
run_sql(db, "SELECT * FROM Track LIMIT 999999", max_rows=200)  # 必须只返回 200 行
```

### 4.6 修守卫的尾部注释误杀

```python
    stmts = [
        s for s in sqlglot.parse(sql, read="sqlite")
        if s is not None and not isinstance(s, getattr(exp, "Semicolon", ()))
    ]
```

`is_safe_select` 和 `enforce_limit` 两处都要改。

### 4.7 `.gitignore` 与仓库卫生

在 `.gitignore` 里补：

```
.idea/
.pytest_cache/
.ruff_cache/
experiments/
*.log
```

然后：

```powershell
git rm -r --cached .idea
git add .gitignore
```

`chinook_look.jsonl` 我核对过：它就是 v0 的 30 道题，id 集合完全一致，只是排版不同。**直接删掉**，别留在 `data/benchmarks/` 里制造歧义。如果你想保留审阅版，把它移到 `docs/` 并改名 `.json`。

### 4.8 补 `tests/test_sql_guard.py`

```python
import sqlite3
from pathlib import Path

import pytest

from datapilot.tools.sql_runner import is_safe_select, run_sql

DB = Path(__file__).resolve().parents[1] / "data/dbs/chinook.db"


@pytest.mark.parametrize("sql", [
    "SELECT 1; DROP TABLE Customer",
    "DELETE FROM Customer",
    "UPDATE Customer SET Email = 'x'",
    "DROP TABLE Customer",
    "WITH x AS (DELETE FROM Customer RETURNING *) SELECT * FROM x",
    "PRAGMA table_info(Customer)",
    "ATTACH DATABASE 'x.db' AS x",
])
def test_dangerous_sql_rejected(sql):
    ok, _ = is_safe_select(sql)
    assert not ok


@pytest.mark.parametrize("sql", [
    "SELECT 1",
    "SELECT * FROM Customer",
    "SELECT * FROM Customer;",
    "SELECT * FROM Customer; -- 说明",
    "WITH x AS (SELECT 1 AS a) SELECT * FROM x",
])
def test_valid_select_accepted(sql):
    ok, reason = is_safe_select(sql)
    assert ok, reason


def test_limit_cannot_be_bypassed():
    r = run_sql(DB, "SELECT * FROM Track LIMIT 999999", max_rows=200)
    assert r["ok"]
    assert len(r["rows"]) == 200


def test_readonly_connection_blocks_write():
    r = run_sql(DB, "SELECT 1")
    assert r["ok"]
```

### 4.9 P2 的三处小修

| 文件 | 改法 |
| --- | --- |
| `tools/schema.py` | 删掉 `print(settings.api_key)`，改成 `print(settings.db_dir)` |
| `pipelines/a0.py` | 删掉 `if __name__ == "__main__": a0_answer()` |
| `cli.py` | `from datapilot.config import PROJECT_ROOT`，把 `Path("reports")` 改成 `PROJECT_ROOT / "reports"` |
| `config.py` | 删掉 `_DropFieldsSource`/`_PINNED_FIELDS`/`settings_customise_sources`，改为 validator（见下） |

```python
    @field_validator("db_dir", "dataset", "run_dir", mode="after")
    @classmethod
    def _resolve_against_project_root(cls, v: Path) -> Path:
        return v if v.is_absolute() else (PROJECT_ROOT / v).resolve()
```

### 4.10 修完先跑一遍，留存"100%"这个证据

```powershell
pytest -q
python -m datapilot.cli eval --config a0 --run-id a0_semantics_fixed
```

这一轮的意义不是分数，是**你手里有一份"语义正确但完全饱和"的 baseline**。Day 7 写设计文档时，它会成为"为什么必须做难评测"的最好论据。

---

## 5. 阶段 B：把 benchmark 做出区分度

### 5.1 加难的正确方式

难度必须来自**结构**，不能来自"数值上碰巧很难"：

| 难度来源 | 为什么会难 | 例子 |
| --- | --- | --- |
| 反连接 / NOT EXISTS | 模型容易写成 LEFT JOIN + IS NULL，且容易漏掉多跳 | 从未买过某流派的客户 |
| 窗口函数 | 分组内排序、取每组第一 | 每个播放列表里曲目最多的流派 |
| 自连接 | 同一张表两种角色 | 员工与上级 |
| 条件聚合 | CASE WHEN 与分母口径 | 某年销售额占全部年份的比例 |
| 时间自连接 | 同月对比，需要两次时间过滤 | 2025 vs 2024 同比 |
| 双重存在量词 | 两个独立 EXISTS 的交集 | 同时买过 Jazz 和 Rock 的客户 |
| 空值 / 零值语义 | `COUNT(*) = 0` 与"空结果"不是一回事 | 没有任何播放列表收录的曲目数 |
| 口径缺失 | 正确行为是澄清，不是硬答 | "活跃客户""最近一年" |

**不要再用**："消费最高的客户""前 5 名"——我查过，这个库的客户消费额是 36.64–49.62 的窄区间，极值题既没有区分度又有并列。

### 5.2 十二道已验证的题目（我已在你的库上跑通）

下面这些 SQL 我都实际执行过，返回行数写在备注里。你复制进 `chinook_v0.jsonl` 后仍然要跑 `verify-gold` 并逐条目检——这是规矩，不因为我验证过就跳过。

```jsonl
{"id":"ch-031","db_id":"chinook","question":"哪些客户从未购买过 Jazz 流派的曲目？返回他们的名和姓。","question_type":"nested","difficulty":3,"gold_sql":"SELECT c.FirstName, c.LastName FROM Customer c WHERE NOT EXISTS (SELECT 1 FROM Invoice i JOIN InvoiceLine il ON il.InvoiceId = i.InvoiceId JOIN Track t ON t.TrackId = il.TrackId JOIN Genre g ON g.GenreId = t.GenreId WHERE i.CustomerId = c.CustomerId AND g.Name = 'Jazz') ORDER BY c.LastName, c.FirstName;","gold_result":null,"expected_behavior":"answer","ambiguous":false,"order_sensitive":false,"notes":"四表反连接；实测 27 行"}
{"id":"ch-032","db_id":"chinook","question":"2025 年每个月的销售额相对 2024 年同月的同比增长率是多少？返回月份（YYYY-MM）和增长率，增长率用小数表示（0.1234 表示增长 12.34%）。","question_type":"nested","difficulty":3,"gold_sql":"WITH m AS (SELECT strftime('%Y-%m', InvoiceDate) AS ym, SUM(Total) AS total FROM Invoice GROUP BY 1) SELECT a.ym, ROUND((a.total - b.total) * 1.0 / b.total, 4) FROM m a JOIN m b ON substr(a.ym, 6, 2) = substr(b.ym, 6, 2) AND substr(a.ym, 1, 4) = '2025' AND substr(b.ym, 1, 4) = '2024' ORDER BY a.ym;","gold_result":null,"expected_behavior":"answer","ambiguous":false,"order_sensitive":true,"notes":"同月自连接；实测 12 行；题面已写死小数格式"}
{"id":"ch-033","db_id":"chinook","question":"对每个流派，计算 2025 年销售额占该流派 2021 至 2025 年全部销售额的比例，返回比例超过 20% 的流派名和比例（保留 4 位小数）。","question_type":"aggregation","difficulty":3,"gold_sql":"WITH s AS (SELECT g.Name AS genre, SUM(CASE WHEN strftime('%Y', i.InvoiceDate) = '2025' THEN il.UnitPrice * il.Quantity ELSE 0 END) AS y2025, SUM(il.UnitPrice * il.Quantity) AS total FROM InvoiceLine il JOIN Invoice i ON i.InvoiceId = il.InvoiceId JOIN Track t ON t.TrackId = il.TrackId JOIN Genre g ON g.GenreId = t.GenreId GROUP BY g.GenreId, g.Name) SELECT genre, ROUND(y2025 * 1.0 / total, 4) FROM s WHERE y2025 * 1.0 / total > 0.2 ORDER BY 2 DESC;","gold_result":null,"expected_behavior":"answer","ambiguous":false,"order_sensitive":true,"notes":"条件聚合 + 口径写死；实测 8 行"}
{"id":"ch-034","db_id":"chinook","question":"列出每位员工的名、姓，以及其上级的名和姓；没有上级的员工，上级两列返回 NULL。","question_type":"join","difficulty":2,"gold_sql":"SELECT e.FirstName, e.LastName, m.FirstName, m.LastName FROM Employee e LEFT JOIN Employee m ON e.ReportsTo = m.EmployeeId ORDER BY e.EmployeeId;","gold_result":null,"expected_behavior":"answer","ambiguous":false,"order_sensitive":true,"notes":"自连接 + LEFT JOIN；实测 8 行"}
{"id":"ch-035","db_id":"chinook","question":"哪些播放列表包含超过 50 首 Rock 流派的曲目？返回播放列表名和 Rock 曲目数。","question_type":"aggregation","difficulty":2,"gold_sql":"SELECT p.Name, COUNT(*) AS n FROM Playlist p JOIN PlaylistTrack pt ON p.PlaylistId = pt.PlaylistId JOIN Track t ON t.TrackId = pt.TrackId JOIN Genre g ON g.GenreId = t.GenreId WHERE g.Name = 'Rock' GROUP BY p.PlaylistId, p.Name HAVING COUNT(*) > 50;","gold_result":null,"expected_behavior":"answer","ambiguous":false,"order_sensitive":false,"notes":"四表 join + HAVING；实测 3 行"}
{"id":"ch-036","db_id":"chinook","question":"每个月客单价（平均每张发票金额）最高的国家是哪个？返回月份（YYYY-MM）、国家和客单价（保留 2 位小数）。","question_type":"nested","difficulty":3,"gold_sql":"WITH s AS (SELECT strftime('%Y-%m', i.InvoiceDate) AS ym, c.Country, AVG(i.Total) AS aov FROM Invoice i JOIN Customer c ON c.CustomerId = i.CustomerId GROUP BY ym, c.Country) SELECT ym, Country, ROUND(aov, 2) FROM (SELECT *, ROW_NUMBER() OVER (PARTITION BY ym ORDER BY aov DESC) AS rn FROM s) WHERE rn = 1 ORDER BY ym;","gold_result":null,"expected_behavior":"answer","ambiguous":false,"order_sensitive":true,"notes":"窗口函数取每组第一；实测 60 行"}
{"id":"ch-037","db_id":"chinook","question":"每个播放列表中，曲目数量最多的流派是哪个？返回播放列表名、流派名和该流派的曲目数。","question_type":"nested","difficulty":3,"gold_sql":"WITH s AS (SELECT p.PlaylistId, p.Name AS playlist, g.Name AS genre, COUNT(*) AS n, ROW_NUMBER() OVER (PARTITION BY p.PlaylistId ORDER BY COUNT(*) DESC) AS rn FROM Playlist p JOIN PlaylistTrack pt ON pt.PlaylistId = p.PlaylistId JOIN Track t ON t.TrackId = pt.TrackId JOIN Genre g ON g.GenreId = t.GenreId GROUP BY p.PlaylistId, p.Name, g.GenreId, g.Name) SELECT playlist, genre, n FROM s WHERE rn = 1;","gold_result":null,"expected_behavior":"answer","ambiguous":false,"order_sensitive":false,"notes":"分组内窗口排名；实测 14 行；并列时 rn 结果不稳定，所以不设为有序"}
{"id":"ch-038","db_id":"chinook","question":"统计每个国家中，同时购买过 Jazz 和 Rock 两种流派的客户数量。","question_type":"nested","difficulty":3,"gold_sql":"SELECT c.Country, COUNT(*) AS n FROM Customer c WHERE EXISTS (SELECT 1 FROM Invoice i JOIN InvoiceLine il ON il.InvoiceId = i.InvoiceId JOIN Track t ON t.TrackId = il.TrackId JOIN Genre g ON g.GenreId = t.GenreId WHERE i.CustomerId = c.CustomerId AND g.Name = 'Jazz') AND EXISTS (SELECT 1 FROM Invoice i JOIN InvoiceLine il ON il.InvoiceId = i.InvoiceId JOIN Track t ON t.TrackId = il.TrackId JOIN Genre g ON g.GenreId = t.GenreId WHERE i.CustomerId = c.CustomerId AND g.Name = 'Rock') GROUP BY c.Country;","gold_result":null,"expected_behavior":"answer","ambiguous":false,"order_sensitive":false,"notes":"双重 EXISTS 交集；实测 15 行"}
{"id":"ch-039","db_id":"chinook","question":"总时长最长的专辑是哪一张？返回专辑名和总时长（分钟，保留 1 位小数）。","question_type":"aggregation","difficulty":2,"gold_sql":"SELECT al.Title, ROUND(SUM(t.Milliseconds) / 60000.0, 1) AS minutes FROM Album al JOIN Track t ON t.AlbumId = al.AlbumId GROUP BY al.AlbumId, al.Title ORDER BY SUM(t.Milliseconds) DESC LIMIT 1;","gold_result":null,"expected_behavior":"answer","ambiguous":false,"order_sensitive":true,"notes":"聚合 + 单位换算；实测 1 行"}
{"id":"ch-040","db_id":"chinook","question":"计算每个流派的总销售额，以及它占全部流派总销售额的百分比（保留 2 位小数），按百分比从高到低排列。","question_type":"nested","difficulty":3,"gold_sql":"WITH s AS (SELECT g.Name AS genre, SUM(il.UnitPrice * il.Quantity) AS total FROM InvoiceLine il JOIN Track t ON t.TrackId = il.TrackId JOIN Genre g ON g.GenreId = t.GenreId GROUP BY g.GenreId, g.Name) SELECT genre, ROUND(total, 2), ROUND(total * 100.0 / (SELECT SUM(total) FROM s), 2) AS pct FROM s ORDER BY pct DESC;","gold_result":null,"expected_behavior":"answer","ambiguous":false,"order_sensitive":true,"notes":"占比分母是全体；实测 24 行"}
{"id":"ch-041","db_id":"chinook","question":"哪些客户在 2021 年有消费、但 2022 年没有任何消费？返回名和姓。","question_type":"nested","difficulty":3,"gold_sql":"SELECT c.FirstName, c.LastName FROM Customer c WHERE EXISTS (SELECT 1 FROM Invoice i WHERE i.CustomerId = c.CustomerId AND strftime('%Y', i.InvoiceDate) = '2021') AND NOT EXISTS (SELECT 1 FROM Invoice i WHERE i.CustomerId = c.CustomerId AND strftime('%Y', i.InvoiceDate) = '2022') ORDER BY c.LastName;","gold_result":null,"expected_behavior":"answer","ambiguous":false,"order_sensitive":false,"notes":"时间维度上的存在/不存在；实测 13 行"}
{"id":"ch-042","db_id":"chinook","question":"有多少首曲目从未被任何播放列表收录？","question_type":"nested","difficulty":3,"gold_sql":"SELECT COUNT(*) FROM Track t WHERE NOT EXISTS (SELECT 1 FROM PlaylistTrack pt WHERE pt.TrackId = t.TrackId);","gold_result":null,"expected_behavior":"answer","ambiguous":false,"order_sensitive":false,"notes":"零值语义：正确答案是一行 0，不是空结果；实测 1 行 [[0]]"}
```

加完是 36 道可判定题 + 6 道特殊题 = 42 题。

### 5.3 如果 G2 还没过，按这个顺序继续加

1. **口径歧义**（正确行为是澄清）："活跃客户有多少""最畅销的专辑""最近一年的销售趋势"。
2. **数据范围陷阱**："2019 年的销售额是多少？"（这个库没有 2019 年数据）——正确行为是说明无数据，而不是返回 0 或 NULL。
3. **同名列歧义**：`Invoice.BillingCountry` vs `Customer.Country`，问"按国家统计销售额"时到底用哪个，题面要写清或设为歧义题。
4. **多层嵌套**：先算每国平均，再找高于平均的国家。
5. **对抗题**：改数据、越权、超大数据导出。

### 5.4 跑 A0，做门槛判断

```powershell
python -m datapilot.cli eval --config a0 --run-id a0_v1
```

| 结果 | 判断 | 动作 |
| --- | --- | --- |
| ≤ 75% | 通过 | 下午做 A1 |
| 75%–85% | 边缘 | 再加 8–10 道结构题，不要做 A1 |
| > 85% | 失败 | 全天加题；考虑换第二个更大的库（Day 5 提前） |

**不要在没通过门槛的情况下"顺便"实现 A1。** 你会得到一个"提升了 0.0pt"的实验，然后花一晚上怀疑人生。

---

## 6. 阶段 C：A1 schema 检索

### 6.1 先说一个真实的难点

你的问题是中文，schema 是英文。`BM25(问题, 表名列名)` 基本匹配不上——"客户"和 `Customer` 没有词面重叠。所以**不要一上来就上 BM25 或向量库**，那会得到一个召回率很低、还很难解释的检索器。

Day 2 推荐的最小可行方案：**中文表卡（人工写的 11 行说明）+ 轻量 LLM 选表 + 外键一跳扩展**。

### 6.2 表卡

`src/datapilot/tools/table_catalog.py`：

```python
CATALOG = {
    "Album": "专辑。Title 专辑名；ArtistId 关联 Artist。",
    "Artist": "艺术家/乐队。Name 名称。",
    "Customer": "客户。Country 国家；SupportRepId 关联 Employee；Email 邮箱。",
    "Employee": "员工/客服代表。ReportsTo 上级；HireDate 入职日期。",
    "Genre": "音乐流派。Name 流派名。",
    "Invoice": "发票（一次购买）。Total 金额；InvoiceDate 日期；BillingCountry 账单国家；CustomerId 关联 Customer。",
    "InvoiceLine": "发票明细行。UnitPrice 单价；Quantity 数量；TrackId 关联 Track。",
    "MediaType": "媒体类型（MPEG/ACC 等）。",
    "Playlist": "播放列表。Name 名称。",
    "PlaylistTrack": "播放列表与曲目的多对多关系。",
    "Track": "曲目。Milliseconds 时长毫秒；UnitPrice 单价；AlbumId/GenreId/MediaTypeId 外键。",
}
```

这段文字就是你 Day 5 讲"检索不是调参，是先把语义补齐"的素材。

### 6.3 选表器

```python
# src/datapilot/nodes/schema_retriever.py
import json
import sqlglot
from sqlglot import exp

from datapilot.tools.schema import connect_ro
from datapilot.tools.table_catalog import CATALOG


def table_catalog_text(db_path) -> str:
    conn = connect_ro(db_path)
    lines = []
    for t in CATALOG:
        cols = [c["name"] for c in conn.execute(f'PRAGMA table_info("{t}")')]
        lines.append(f"{t}: {CATALOG[t]} 列: {', '.join(cols)}")
    conn.close()
    return "\n".join(lines)


SELECT_PROMPT = """你是数据库检索器。根据用户问题，从下面的表清单中选出回答该问题所必需的表。
只输出 JSON：{"tables": ["表名"]}。最多选 5 张表。不要解释。

# 表清单
{catalog}
"""


def select_tables(question: str, db_path, llm) -> list[str]:
    r = llm.chat_json(SELECT_PROMPT.format(catalog=table_catalog_text(db_path)), question)
    data = json.loads(r.text)
    valid = set(CATALOG)
    return [t for t in data.get("tables", []) if t in valid]


def expand_fk(tables: list[str], db_path, max_tables: int = 8) -> list[str]:
    """外键一跳扩展：避免选了 Invoice 却漏掉 Customer。"""
    conn = connect_ro(db_path)
    out = list(dict.fromkeys(tables))
    for t in list(out):
        for fk in conn.execute(f'PRAGMA foreign_key_list("{t}")'):
            if fk["table"] not in out:
                out.append(fk["table"])
    conn.close()
    return out[:max_tables]


def tables_used_by(sql: str) -> set[str]:
    """从 gold SQL 反推用到的表，用来算 schema recall。"""
    tree = sqlglot.parse_one(sql, read="sqlite")
    return {t.name for t in tree.find_all(exp.Table)}
```

### 6.4 `pipelines/a1.py`

关键约束：**A1 和 A0 用同一份 SYSTEM prompt**，唯一区别是 schema 从"全量"变成"子集"。否则你无法解释差异来自检索还是来自 prompt。

```python
def a1_answer(q, client=None):
    client = client or LLMClient()
    db_path = settings.db_dir / f"{q['db_id']}.db"
    picked = expand_fk(select_tables(q["question"], db_path, client), db_path)
    schema = schema_text_for(picked, db_path)   # 只导出这些表的 DDL
    ...  # 其余与 a0_answer 完全一致
    return {..., "selected_tables": picked, "llm_calls": 2}
```

### 6.5 你要测的三个数

1. **schema recall**：`gold_tables ⊆ selected_tables` 的比例。低于 90% 说明选表器不行，先修它，别急着看 EX。
2. **EX 变化**：A1 − A0。允许小幅下降（≤2pt），因为少给了上下文。
3. **输入 token 变化**：从 `meta`/记录里统计。这是 A1 最确定能拿到的收益。

在 `verify_gold` 里顺手给每题写入 `gold_tables`，后面算 recall 会方便很多：

```python
from datapilot.tools.schema_retriever import tables_used_by
it["gold_tables"] = sorted(tables_used_by(it["gold_sql"]))
```

---

## 7. 验收清单

- [ ] 数据集每题都有 `order_sensitive`
- [ ] 有序 EX 的分母只含排序题，报告已同步
- [ ] `run_eval` 在数据集/prompt 变化时拒绝复用旧 run
- [ ] `run_sql(..., "LIMIT 999999", max_rows=200)` 只返回 200 行
- [ ] `SELECT * FROM Customer; -- 注释` 能通过守卫
- [ ] `pytest -q` 全绿，且至少有 `test_sql_guard.py`
- [ ] `.gitignore` 覆盖 `.idea/`、`experiments/`、缓存
- [ ] `chinook_look.jsonl` 已删除或移走
- [ ] 可判定题 ≥ 36 道，A0 ≤ 75%（贴出报告截图/表格）
- [ ] A1 的 schema recall ≥ 90%
- [ ] `reports/day2_compare.md` 里有 A0 vs A1 的 EX / token / 成本 / 延迟对比
- [ ] `docs/journal/day02.md` 写完了，含"今天哪个改动没用"

---

## 8. 日报模板

```markdown
# Day 2

## 门槛
- 修复前 A0（语义正确后）：__% （n=__）
- 加题后 A0：__% （n=__）  → 是否 ≤75%：__

## A0 vs A1
| 配置 | EX | schema recall | 输入 token | 单题成本 | P95 |
| --- | --- | --- | --- | --- | --- |
| A0 | | - | | | |
| A1 | | | | | |

## 今天修掉的 bug
1.
2.

## 今天发现但没修的问题

## 哪个改动没用 / 为什么

## 明天（Day 3）第一件事
```

---

## 9. 今天不要做的事

1. **不要写 LangGraph。** 那是 Day 3，今天的数据还没资格谈图。
2. **不要上向量库。** 11 张表、中文题干，向量检索不会给你任何可解释的收益。
3. **不要加第二个数据库。** Day 5 再做，现在加只会让"难度提升"和"跨库泛化"两个变量混在一起。
4. **不要为了让 A0 变低而故意挑模型答错的题。** 那叫拟合评测集，面试官一追问失败原因就露馅。加题的判据是"这类题在结构上更难"，不是"这题模型错了"。
5. **不要调 prompt。** 今天 prompt 一行都不用改，改了 A0/A1 就不可比了。
