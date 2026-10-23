# Day 3 实施手册 —— LangGraph 主图 + 带"检索扩大"的修复环

> 前置：Day 2 已完成（4 组 run + top_k 敏感性实验）。
> 本手册相对总手册 Day 3 有一处**由数据驱动的新设计**：修复环增加"检索扩大"逃生通道。理由在第 1 章，这是你自己跑出来的结论，不是抄来的。

---

## 0. 开工前：收口三件事（90 分钟，先做再做主任务）

### 0.1 top_k 配置化 + meta 记录（45 分钟）

现在的 top_k=6 是写在 `a1.py` 函数默认值里的，`meta.json` 完全没有记录。一周后你无法从 meta 区分 `a1_chinook`（k=4）和 `a1_chinook_fix`（k=6），靠 run_id 后缀记性是脆弱的。修掉它：

**新建 `eval/configs/a1.yaml`：**

```yaml
pipeline: a0
```

**新建 `eval/configs/a1.yaml`：**

```yaml
pipeline: a1
top_k: 6
```

**新建 `eval/configs/a2.yaml`（下午就用）：**

```yaml
pipeline: a2
top_k: 6
repair_max_attempts: 3
```

**新建 `src/datapilot/eval/eval_config.py`：**

```python
# 评测配置加载与指纹。指纹必须覆盖配置内容——否则同 run_id 换了 top_k 会静默续跑，
# 把两次不同配置的实验结果混进同一个 results.jsonl，消融直接报废。

import hashlib
from pathlib import Path

import yaml


def load_eval_config(name: str) -> dict:
    p = Path("eval/configs") / f"{name}.yaml"
    if not p.exists():
        raise FileNotFoundError(f"缺少配置文件：{p}")
    cfg = yaml.safe_load(p.read_text(encoding="utf-8"))
    cfg["name"] = name
    return cfg


def config_fingerprint(cfg: dict) -> str:
    blob = yaml.safe_dump({k: v for k, v in cfg.items() if k != "name"}, sort_keys=True)
    return hashlib.md5(blob.encode()).hexdigest()[:12]
```

**runner.py 的三处改动**

**改动①：**入口加载 cfg + 改动③：pipeline 分发（这两处长在了一起）

**顶部 import 增加：**

python

```python
from datapilot.eval.eval_config import config_fingerprint, load_eval_config
```

**把 `get_pipeline` 从 cli.py 移到 runner.py**（分发是 runner 的职责，且 cli 现在传 string 是断的）。放在 `prompt_fingerprint()` 之后：

```python
def get_pipeline(cfg: dict) -> Callable[[dict], dict]:
    """按 cfg["pipeline"] 分发，并把 cfg 里的参数绑定进 pipeline 调用。"""
    name = cfg["pipeline"]
    if name == "a0":
        from datapilot.pipelines.a0 import a0_answer
        return lambda q: a0_answer(q)
    if name == "a1":
        from datapilot.pipelines.a1 import a1_answer
        top_k = cfg.get("top_k", 6)
        return lambda q: a1_answer(q, top_k=top_k)
    if name == "a2":
        from datapilot.pipelines.a2 import graph_answer
        return lambda q: graph_answer(q, cfg=cfg)
    raise ValueError(f"未知 pipeline：{name}")
```

两个细节：

- **分支内 lazy import 必须保留**——a2.py 还不存在，这样写 a0/a1 照常能跑，`--config a2` 在图实现前会报 `ModuleNotFoundError`，这是预期行为；
- lambda 只收 `q` 一个参数。旧 cli 版的 `(q, client=None)` 里 client 从没被 runner 传过，是死参数，删掉。

**`run_eval` 签名与入口改写**（删掉第一个 `pipeline_fn` 参数）：

```python
def run_eval(
    *,
    config_name: str,
    dataset_path: str | Path | None = None,
    run_id: str | None = None,
    limit: int | None = None,
    concurrency: int | None = None,
) -> dict:
    cfg = load_eval_config(config_name)      # 改动①：配置即实验身份
    pipeline_fn = get_pipeline(cfg)          # 改动③：按 cfg 分发并绑定
    dataset_path = Path(dataset_path or settings.dataset)
    # ……后续不变
```

**改动②：**指纹升级 + meta 落盘

**`run_fingerprint` 改为三段式：**

```python
def run_fingerprint(dataset_path: str | Path, cfg: dict) -> str:
    """三段式指纹：数据集 + prompt + 评测配置。任何一段变了都不许续跑。"""
    return (
        f"{dataset_fingerprint(dataset_path)}"
        f"-{prompt_fingerprint()}"
        f"-{config_fingerprint(cfg)}"
    )
```

**`run_eval` 里调用处：**

```python
fp = run_fingerprint(dataset_path, cfg)
```

**续跑报错文案同步更新**（配置变化也会走到这个分支）：

```python
raise RuntimeError(
    f"数据集、prompt 或评测配置已变化（{old['fingerprint']} -> {fp}）。"
    f"请换一个 run_id，或删除 {run_dir}。"
)
```

**meta dict 里加一行：**

```python
    "fingerprint": fp,
    "eval_config": cfg,        # 改动②：完整配置落盘（含 top_k / repair_max_attempts）
    "model": settings.model,
```

cli.py 配套修改

1. **删掉整个 `get_pipeline` 函数**（已移入 runner）；
2. `cmd_eval` 改为：

```python
fn 行删除，直接：
    out = run_eval(
        config_name=config,
        dataset_path=dataset or None,
        limit=limit or None,
        concurrency=concurrency or None,
        run_id=run_id or None,
    )
```

我确认过全仓库只有 cli.py 这一个调用点，没有测试直接调 `run_eval`，签名改动是安全的。

验证清单（按顺序做）

```bash
# 1. 冒烟：a0 跑 2 题
.venv/Scripts/python -m src.datapilot.cli eval --config a0 --limit 2 --run-id cfg_smoke

# 2. 检查 meta：应看到 eval_config 字段和三段式 fingerprint
cat experiments/runs/cfg_smoke/meta.json

# 3. 同 run_id 重跑 → 应零新增调用（n_pending=0）
.venv/Scripts/python -m src.datapilot.cli eval --config a0 --run-id cfg_smoke

# 4. 改一下 a0.yaml（比如加个注释外的字段）再同 run_id 跑 → 必须 raise 指纹 mismatch
#    验证完恢复 a0.yaml

# 5. 单测仍全绿
.venv/Scripts/python -m pytest -q
```

验证通过后删掉 `experiments/runs/cfg_smoke/`。





### 0.2 填 Day 2 日报（30 分钟）

`docs/journal/day02.md` 还是空模板。数字我已经替你核算过，直接填：

**对比表（top_k=6，run 后缀 _fix）：**

| run | EX（无序） | 排序题 EX | 召回率 | 检索错/生成错 | ¥/题 |
| --- | --- | --- | --- | --- | --- |
| A0 chinook | 100% | 100% (n=15) | — | 0/0 | 0.00376 |
| A1 chinook k=4→6 | 79.17% → 91.67% | 86.67% | 79% → 92% | 5/0 → 2/0 | 0.00312 |
| A0 sakila | 88.89% → 94.44%（同配置两次运行） | 93.33% | — | 0/2 → 0/1 | 0.00382 |
| A1 sakila k=4→6 | 66.67% → 83.33% | 86.67% | 61% → 72% | 6/0 → 3/0 | 0.00556 |

**三个结论（照这个骨架写，用自己的话）：**

1. top_k 4→6 修复 6 道题（ch-003/020/024、sa-002/003/017）、0 道变差，修复的全部是检索错——增益归因无争议；"交白卷 SQL"（`SELECT 0`/`WHERE 1=0`）随召回改善基本消失。
2. 残留 5 道检索错分两类失败模式：词形（sa-013：`films`≠`film`、`rented`≠`rental`，BM25 无词干化）与中英映射（sa-015："演员"→`actor`；ch-021："消费金额"→`Invoice`）。这是向量检索/同义词典存在的证据。
3. A0 sakila 同配置两次运行 88.89%→94.44%（sa-018 翻转）——18 题分母下 1 题 = ±5.5pt，小样本波动的活实例。

### 0.3 把"检索扩大"写进设计（15 分钟，纯思考）

先读懂这个逻辑链，它是今天全部工作的出发点：

1. Day 2 数据：A1(k=6) 残留的 5 个失败**全部是检索错**，4 组 run 的 SQL 执行错误率全是 0。
2. 总手册原版修复环的触发条件是"执行报错"——**在你的数据集上它不会有输入**，修复增益故事会塌。
3. 所以修复环必须多一条路：诊断发现"schema 疑似不全"（报表不存在/列不存在/可疑空结果）时，不是用同一个 schema 子集重写 SQL，而是**退回全量 schema 重新生成**。
4. 这样 A2 相对 A1 的增益来源就从"修语法错误"升级为"执行反馈驱动的检索-生成协同修复"——叙事更强，且完全由你的数据推导出来。

---

## 1. A2 的定义（公平性红线）

**A2 = A1（top_k=6，冻结）+ 修复环（含检索扩大），其余一切不变。**

- 首次生成的 SYSTEM、模型、温度、JSON 格式与 A0/A1 逐字节一致（继续 `from a0 import SYSTEM`）；
- 唯一的自变量是"失败后有没有第二次机会"；
- 消融口径：修复增益 = A2.EX − A1(k=6).EX，且要用记录里的 `ex_first`（首轮正确率）交叉验证；
- 检索扩大属于 A2 设计的一部分，**必须记录 `escalated` 标志**——透明，而不是藏着。

---

## 2. 图设计（今天的核心，先背下来再写代码）

### 2.1 节点与边

```
START → retrieve → generate → validate → execute → compose → END
                        ↑          |           |
                        |          v           v
                        └── repair ← diagnose ←┘（报错 / 空结果）
                                     |
                                     └→ escalate → retrieve（全量 schema，仅限 1 次）
                                     └→ give_up → compose
```

### 2.2 路由表（背下来，面试照着画）

| 从 | 条件 | 到 |
| --- | --- | --- |
| START | — | retrieve |
| retrieve | — | generate |
| generate | JSON 解析成功 | validate |
| generate | 解析失败且 attempts < 3 | repair |
| validate | 通过守卫 | execute |
| validate | 未通过（危险 SQL） | diagnose（category=unsafe） |
| execute | ok 且 rows > 0 | compose |
| execute | ok 且 rows == 0 | diagnose（可疑空结果判断） |
| execute | 执行报错 | diagnose |
| diagnose | action=repair 且 attempts < 3 | repair |
| diagnose | action=escalate 且未 escalate 过且 attempts < 3 | retrieve（全量） |
| diagnose | 其他（含 unsafe、attempts 耗尽） | give_up |
| repair | — | validate |
| give_up / compose | — | END |

### 2.3 三个关键设计决策（每个都要能讲一分钟）

1. **escalate 是一次性退回全量，不是 top_k 逐级翻倍。** 理由：chinook 11 表、sakila 16 表，6→12 翻倍与全量几乎等价，逐级翻倍只增加状态复杂度。一次到位，成本有界（每题最多 1 次），语义干净。
2. **空结果不直接判失败，先过一道 LLM 判断"可疑吗"。** 空结果可能是正确答案（"不存在 X"类问题）。只有 diagnose 判可疑才进 repair/escalate。代价：空结果题多一次 LLM 调用——值得，因为 Day 2 的失败题大多产出空结果或假零值。
3. **危险 SQL 的归宿是 give_up 而不是 repair。** 模型对"删掉所有客户"生成 DELETE，被守卫拦下后不该"修复"成合法查询——正确行为就是拒答。顺带一个红利：`give_up(unsafe)` 时把 `behavior` 置为 `"refuse"`，对抗题（sa-020、ch-008/030）的行为正确率可能从 0% 涨起来——跑完验证这个猜想，写进日报。

### 2.4 状态定义 `src/datapilot/state.py`

```python
from typing import Any, Optional, TypedDict


class AgentState(TypedDict, total=False):
    # 输入
    question: str
    db_id: str
    trace_id: str
    top_k: int               # 初始 top_k（来自 eval config）
    max_attempts: int

    # 检索
    retrieved_tables: list[str]
    schema_text: str
    escalated: bool          # 是否已退回全量 schema（仅限 1 次）

    # 生成 / 修复
    sql: Optional[str]
    sql_history: list[dict]  # [{sql, error, n_rows, attempt}]
    attempts: int
    first_rows: Optional[list]  # 第一次成功执行的行（算首轮正确率用）

    # 执行
    exec_ok: bool
    error: Optional[str]
    columns: Optional[list]
    rows: Optional[list]
    truncated: bool

    # 诊断
    diagnosis: Optional[dict]  # {category, action, reason}

    # 输出
    behavior: str            # answer / refuse
    give_up_reason: Optional[str]

    # 成本
    cost_cny: float
    in_tokens: int
    llm_calls: int
```

---

## 3. 时间表

| 时段 | 任务 | 产出 |
| --- | --- | --- |
| 0:00–1:30 | 第 0 章三件事 | 配置化完成、day02 日报填满 |
| 1:30–2:00 | 装依赖 + state.py | `uv add langgraph langgraph-checkpoint-sqlite` |
| 2:00–4:00 | 六个节点 | `nodes/*.py` |
| 4:00–5:00 | graph.py + checkpointer | 图编译通过 |
| 5:00–5:40 | runner 对接 + ex_first 指标 | a2 pipeline 注册 |
| 5:40–6:20 | 单测：图冒烟 + 诊断分类 + 守卫路由 | tests 绿 |
| 6:20–7:30 | 跑 A2 × chinook/sakila | 2 个新 run |
| 7:30–8:30 | 分析 + 日报 | day03.md |

允许超时：单测里的 LLM 用例可以减到 1 个。
不允许超时：**diagnoser 的确定性分类单测**（不依赖 LLM，必须稳）。

---

## 4. 节点实现（2 小时）

### 4.1 retrieve / generate / validate / execute 四节点 `src/datapilot/nodes/common_nodes.py`

```python
# 四个主流程节点。generate 的首次生成复用 a0.SYSTEM——公平性红线。

from datapilot.config import settings
from datapilot.llm.client import LLMClient
from datapilot.nodes.schema_retriever import SchemaRetriever
from datapilot.pipelines.a0 import SYSTEM, extract_json
from datapilot.state import AgentState
from datapilot.tools.schema import full_schema_text, schema_text_for
from datapilot.tools.sql_runner import is_safe_select, run_sql

_retrievers: dict[str, SchemaRetriever] = {}


def _retriever(db_id: str) -> SchemaRetriever:
    if db_id not in _retrievers:
        _retrievers[db_id] = SchemaRetriever(settings.db_dir / f"{db_id}.db")
    return _retrievers[db_id]


def node_retrieve(state: AgentState) -> dict:
    db = settings.db_dir / f"{state['db_id']}.db"
    if state.get("escalated"):
        # 检索扩大：一次性退回全量 schema
        tables = [u["table"] for u in _retriever(state["db_id"]).units]
        schema = full_schema_text(db)
    else:
        tables = _retriever(state["db_id"]).retrieve(state["question"], top_k=state["top_k"])
        schema = schema_text_for(db, tables)
    return {"retrieved_tables": tables, "schema_text": schema}


def node_generate(state: AgentState, client: LLMClient) -> dict:
    user = f"# 数据库 Schema\n{state['schema_text']}\n\n# 用户问题\n{state['question']}"
    r = client.chat_json(SYSTEM, user)
    out = {"llm_calls": 1, "cost_cny": r.cost_cny, "in_tokens": r.in_tokens}
    try:
        payload = extract_json(r.text)
        out["sql"] = payload.get("sql", "")
        out["error"] = None
    except Exception as e:
        out["sql"] = None
        out["error"] = f"parse_error: {e}"
    return out


def node_validate(state: AgentState) -> dict:
    ok, reason = is_safe_select(state["sql"] or "")
    return {"exec_ok": False, "error": None if ok else f"unsafe_sql: {reason}"}


def node_execute(state: AgentState) -> dict:
    res = run_sql(
        settings.db_dir / f"{state['db_id']}.db", state["sql"],
        max_rows=settings.max_rows, timeout_s=settings.sql_timeout_s,
    )
    out = {
        "exec_ok": res["ok"], "error": res["error"],
        "columns": res["columns"], "rows": res["rows"] if res["ok"] else None,
        "truncated": res["truncated"],
    }
    if res["ok"] and state.get("first_rows") is None and not state["sql_history"]:
        out["first_rows"] = res["rows"]  # 首轮成功执行的快照，给 ex_first 用
    return out
```

> 注意 LangGraph 的节点约定：返回 dict 是**部分更新**，累加字段（llm_calls、cost_cny）需要在 graph 里用 Reducer 或在 adapter 里汇总。最省事的做法：节点把每次调用追加进 `sql_history`/自定义列表字段，adapter 最后求和。别在节点里做 `state["cost_cny"] + x` 的读改写——并行分支下会丢更新（今天没有并行分支，但养成习惯）。

### 4.2 diagnoser `src/datapilot/nodes/diagnoser.py`

**确定性优先，LLM 只兜底"空结果是否可疑"。** 这样分类逻辑可单测、可复现，不依赖模型心情。

```python
# 诊断节点：确定性规则优先，LLM 只判断"空结果是否可疑"。
# 设计理由：错误分类必须可复现、可单测；LLM 判断被限制在最小范围。

import json

from datapilot.llm.client import LLMClient
from datapilot.state import AgentState

EMPTY_JUDGE = """问题：{question}
SQL：{sql}
执行结果：0 行。
判断这个空结果是否可疑（即：问题语义上是否暗示应该存在数据）。
只输出 JSON：{{"suspicious": true, "reason": "一句话"}}"""


def classify_error(err: str) -> str:
    e = err.lower()
    if "no such table" in e or "no such column" in e:
        return "schema_incomplete"
    if "syntax" in e:
        return "syntax"
    if "unsafe_sql" in e:
        return "unsafe"
    if "parse_error" in e:
        return "parse"
    if "timeout" in e:
        return "timeout"
    return "other"


def node_diagnose(state: AgentState, client: LLMClient) -> dict:
    err = state.get("error")

    # 空结果分支：LLM 判断可疑性
    if not err and state.get("exec_ok") and not state.get("rows"):
        r = client.chat_json(
            "你是严格的评审。",
            EMPTY_JUDGE.format(question=state["question"], sql=state["sql"]),
        )
        try:
            verdict = json.loads(r.text)
            suspicious = bool(verdict.get("suspicious"))
            reason = verdict.get("reason", "")
        except Exception:
            suspicious, reason = True, "LLM 判断解析失败，按可疑处理"
        if not suspicious:
            return {"diagnosis": {"category": "empty_ok", "action": "accept", "reason": reason}}
        category = "empty_suspicious"
    else:
        category = classify_error(err or "")

    # 动作决策：unsafe 直接拒；schema 问题优先扩大检索（仅 1 次）；其余修复
    if category == "unsafe":
        action, reason = "give_up", "危险 SQL 被守卫拦截，正确行为是拒答"
    elif category in ("schema_incomplete", "empty_suspicious") and not state.get("escalated"):
        action, reason = "escalate", "schema 疑似不全，退回全量 schema 重新生成"
    else:
        action, reason = "repair", "带错误反馈修复"

    if state["attempts"] >= state["max_attempts"]:
        action, reason = "give_up", f"attempts 达到上限（{state['max_attempts']}）"

    return {
        "diagnosis": {"category": category, "action": action, "reason": reason},
        "llm_calls": 1 if err is None and category != "unsafe" else 0,
    }
```

> ⚠️ 先核对你 Day 1 写的 `classify_error`（sql_runner 里）输出的错误文本，确保 `"no such table"` 等子串匹配得上。对不上就改这里的子串，**不要改 sql_runner**——它的输出已经被 A0/A1 的历史结果引用。

### 4.3 repairer `src/datapilot/nodes/repairer.py`

```python
# 修复节点：带错误反馈与历史，避免重复同样的错误。

from datapilot.llm.client import LLMClient
from datapilot.pipelines.a0 import extract_json
from datapilot.state import AgentState

REPAIR_SYSTEM = "你是 SQLite 专家。基于执行反馈修复 SQL。只能使用给定 schema 中的表和列。输出严格 JSON。"

REPAIR_USER = """# 数据库 Schema
{schema}

# 原始问题
{question}

# 失败的 SQL
{sql}

# 反馈（报错或诊断）
{feedback}

# 已尝试过的 SQL（不要重复同样的错误）
{history}

输出 JSON：{{"sql": "...", "tables_used": [...], "assumptions": [...]}}"""


def node_repair(state: AgentState, client: LLMClient) -> dict:
    # 只带最近 2 次历史——全塞进去 prompt 膨胀且模型会迷失
    history = "\n".join(
        f"- {h['sql']}  → {h.get('error') or f\"{h.get('n_rows', 0)} 行\"}"
        for h in state["sql_history"][-2:]
    ) or "（无）"
    d = state.get("diagnosis") or {}
    feedback = state.get("error") or f"诊断：{d.get('category')} - {d.get('reason')}"
    r = client.chat_json(REPAIR_SYSTEM, REPAIR_USER.format(
        schema=state["schema_text"], question=state["question"],
        sql=state["sql"], feedback=feedback, history=history,
    ))
    out = {"llm_calls": 1, "cost_cny": r.cost_cny, "in_tokens": r.in_tokens}
    try:
        out["sql"] = extract_json(r.text).get("sql", "")
        out["error"] = None
    except Exception as e:
        out["error"] = f"parse_error: {e}"
    return out
```

### 4.4 give_up 与 compose

```python
# src/datapilot/nodes/terminal_nodes.py

from datapilot.state import AgentState


def node_give_up(state: AgentState) -> dict:
    d = state.get("diagnosis") or {}
    reason = d.get("reason") or "unknown"
    out = {"give_up_reason": reason, "rows": None}
    # 危险 SQL 被拦截 → 这是正确的拒答行为，不是失败
    if d.get("category") == "unsafe":
        out["behavior"] = "refuse"
    return out


def node_compose(state: AgentState) -> dict:
    # Day 3 的 compose 是 lite 版：不做自然语言结论（Day 4 的 answer_composer 再做）
    return {}
```

---

## 5. 图构建 `src/datapilot/graph.py`

```python
# A2 的图。checkpointer 的 thread_id 用 f"{run_id}:{question_id}"——
# 跨 run 复用同一 checkpoints.db 时旧 state 会污染新 run。

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from datapilot.llm.client import LLMClient
from datapilot.nodes.common_nodes import (
    node_execute, node_generate, node_retrieve, node_validate,
)
from datapilot.nodes.diagnoser import node_diagnose
from datapilot.nodes.repairer import node_repair
from datapilot.nodes.terminal_nodes import node_compose, node_give_up
from datapilot.state import AgentState

_client: LLMClient | None = None


def _get_client() -> LLMClient:
    global _client
    if _client is None:
        _client = LLMClient()
    return _client


def build_graph(checkpoint_db: str):
    g = StateGraph(AgentState)
    g.add_node("retrieve", node_retrieve)
    g.add_node("generate", lambda s: node_generate(s, _get_client()))
    g.add_node("validate", node_validate)
    g.add_node("execute", node_execute)
    g.add_node("diagnose", lambda s: node_diagnose(s, _get_client()))
    g.add_node("repair", lambda s: node_repair(s, _get_client()))
    g.add_node("give_up", node_give_up)
    g.add_node("compose", node_compose)

    g.add_edge(START, "retrieve")
    g.add_edge("retrieve", "generate")
    g.add_conditional_edges("generate",
        lambda s: "validate" if s.get("sql") else "diagnose",
        {"validate": "validate", "diagnose": "diagnose"})
    g.add_conditional_edges("validate",
        lambda s: "execute" if not s.get("error") else "diagnose",
        {"execute": "execute", "diagnose": "diagnose"})
    g.add_conditional_edges("execute", _route_after_execute,
        {"compose": "compose", "diagnose": "diagnose"})
    g.add_conditional_edges("diagnose", _route_after_diagnose,
        {"repair": "repair", "escalate": "retrieve", "accept": "compose", "give_up": "give_up"})
    g.add_edge("repair", "validate")
    g.add_edge("give_up", "compose")
    g.add_edge("compose", END)

    cp = SqliteSaver.from_conn_string(checkpoint_db)
    return g.compile(checkpointer=cp)


def _route_after_execute(s: AgentState) -> str:
    if s["exec_ok"] and s.get("rows"):
        return "compose"
    return "diagnose"  # 报错或空结果都进诊断


def _route_after_diagnose(s: AgentState) -> str:
    action = (s.get("diagnosis") or {}).get("action", "give_up")
    if action == "escalate":
        return "escalate"
    if action == "repair" and s["attempts"] < s["max_attempts"]:
        return "repair"
    if action == "accept":
        return "accept"
    return "give_up"
```

** escalate 边的一个细节**：diagnose → retrieve 重进检索时，要在进入前把 `escalated` 置 True 且 `attempts += 1`。两种做法：单独加一个 `escalate` 节点（推荐，显式、可查 trace），或在 diagnose 里就地更新。用显式节点：

```python
def node_escalate(state: AgentState) -> dict:
    return {"escalated": True, "attempts": state["attempts"] + 1}
```

对应把边改成 `{"escalate": "escalate", ...}` + `g.add_edge("escalate", "retrieve")`。

**attempts 在哪里加**：repair 节点返回里 `"attempts": state["attempts"] + 1`。每次循环必须有人加，没人加就是无限循环。

**sql_history 在哪里追加**：execute 节点末尾追加 `{"sql", "error", "n_rows", "attempt"}`——它是修复上下文的数据源。

---

## 6. runner 对接 + 首轮正确率（40 分钟）

### 6.1 适配器 `src/datapilot/pipelines/a2.py`

```python
# A2 = A1(top_k 冻结) + 修复环。pipeline_fn 接口与 a0/a1 完全对齐——
# 这是 Day 1 接口设计的兑现时刻：runner 一行不改。

import json
import time

from datapilot.config import settings
from datapilot.graph import build_graph


def graph_answer(q: dict, client=None, cfg: dict | None = None) -> dict:
    cfg = cfg or {}
    t0 = time.perf_counter()
    trace_id = f"a2-{q['id']}"
    app = build_graph("checkpoints.db")
    final = app.invoke(
        {
            "question": q["question"], "db_id": q["db_id"], "trace_id": trace_id,
            "top_k": cfg.get("top_k", 6),
            "max_attempts": cfg.get("repair_max_attempts", 3),
            "attempts": 0, "escalated": False, "sql_history": [],
            "behavior": "answer", "cost_cny": 0.0, "in_tokens": 0, "llm_calls": 0,
        },
        config={"configurable": {"thread_id": f"{cfg.get('name', 'a2')}:{q['id']}"}},
    )
    return {
        "status": "ok" if final.get("exec_ok") else "sql_error",
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
            "first_rows": final.get("first_rows"),   # runner 算完 ex_first 后会丢掉
            "diagnosis": final.get("diagnosis"),
        },
    }
```

> 上面的累加字段（cost_cny 等）依赖你在图里正确处理 Reducer。LangGraph 里给 `AgentState` 的累加字段标注 `Annotated[float, operator.add]` 是最干净的做法——查一下你装的 langgraph 版本的 Reducer 写法，照做。

### 6.2 runner 增加首轮正确率

`runner.py` 的 `score_one` 里，extra 处理后加：

```python
    # 首轮正确率：pipeline 上报了 first_rows 才算（A2 类 run）
    if q["expected_behavior"] == "answer" and "first_rows" in extra:
        fa = extra.pop("first_rows")  # 行数据不进 results.jsonl，太占地方
        extra["ex_first"] = (
            results_equal(fa, gold, order_sensitive=bool(q.get("order_sensitive")),
                          ndigits=settings.round_ndigits, casefold=settings.casefold)
            if fa is not None else False
        )
```

`metrics.py` 的 `aggregate` 加：

```python
        ex_firsts = [r["ex_first"] for r in answerable if "ex_first" in r]
        "ex_first": round(sum(ex_firsts) / len(ex_firsts), 4) if ex_firsts else None,
        # 修复增益 = 最终 EX − 首轮正确率。本项目最想证明的数字。
        "repair_gain": (
            round(ex / len(answerable) - sum(ex_firsts) / len(ex_firsts), 4)
            if ex_firsts and answerable else None
        ),
        "n_escalated": sum(1 for r in records if r.get("escalated")),
```

report.py 对应加三行（首轮正确率 / 修复增益 / 触发检索扩大次数），注意 None 处理。

---

## 7. 单测（40 分钟）

`tests/test_graph_smoke.py`：

```python
from datapilot.eval.eval_config import load_eval_config
from datapilot.nodes.diagnoser import classify_error


def test_classify_error_deterministic():
    assert classify_error("no such table: Foo") == "schema_incomplete"
    assert classify_error("no such column: x") == "schema_incomplete"
    assert classify_error('near "SELET": syntax error') == "syntax"
    assert classify_error("unsafe_sql: 非 SELECT/WITH") == "unsafe"
    assert classify_error("parse_error: xxx") == "parse"


def test_unsafe_gives_refuse():
    # 危险 SQL → give_up → behavior=refuse，不需要 LLM
    from datapilot.nodes.terminal_nodes import node_give_up
    out = node_give_up({"diagnosis": {"category": "unsafe", "reason": "r"}, "rows": [1]})
    assert out["behavior"] == "refuse" and out["rows"] is None


def test_graph_smoke_real_llm():
    # 全图冒烟：1 道真题，断言接口字段齐全（需要 API Key，CI 可跳过）
    import json
    q = {"id": "ch-001", "db_id": "chinook",
         "question": "列出所有巴西客户的姓名和邮箱。"}
    from datapilot.pipelines.a2 import graph_answer
    out = graph_answer(q, cfg=load_eval_config("a2"))
    for k in ("status", "sql", "rows", "behavior", "retrieved_tables"):
        assert k in out
    assert out["status"] == "ok"
```

---

## 8. 跑 A2 与解读规则（70 分钟）

```powershell
# 冒烟：1 道已知会触发 escalate 的题（sa-013 在 k=6 下漏 film/inventory）
python -m src.datapilot.cli eval --config a2 --dataset data/benchmarks/sakila_v0.jsonl --limit 3 --run-id a2_smoke

# 正式两组（顺序跑）
python -m src.datapilot.cli eval --config a2 --run-id a2_chinook
python -m src.datapilot.cli eval --config a2 --dataset data/benchmarks/sakila_v0.jsonl --run-id a2_sakila
```

**解读规则（对号入座）：**

- **A2 chinook → ~100%**：符合预期——残留 2 道（ch-021/022）是检索错，escalate 退回全量后应能修。若仍失败，去 trace 看 diagnoser 把空结果判成了什么。
- **A2 sakila 显著提升（83% → 90%+）**：escalate 修检索错；sa-014（结果错但无报错）修不了，那是 Day 4 verifier 的靶子，如实写。
- **修复增益 ≈ 0 且 n_escalated = 0**：diagnoser 没触发——八成是空结果判断太宽松，或 escalate 条件没命中。打印每道失败题的 `diagnosis` 排查。
- **A2 在某题上反而变差**：大概率是 escalate 后全量 schema 干扰了原本正确的生成。这是真实发现，写进日报，别藏。
- **特殊题行为正确率从 0% 涨了**：验证 2.3 决策 3 的红利猜想，这是意外收获，重点写。

**验收演示**：从 results.jsonl 里挑一道"首轮失败 → escalate/repair → 成功"的题，把 `sql_history` + `diagnosis` 打出来，这就是"第一次报错 → 自动修复 → 成功"的 trace 证据。

---

## 9. Day 3 日报模板

```markdown
# Day 3

## 目标完成度
- [ ] top_k 配置化 + meta 记录（指纹覆盖配置内容）
- [ ] day02 日报填满
- [ ] 图 + 修复环 + 检索扩大逃生通道
- [ ] checkpointer 接入（thread_id = config名:题id）
- [ ] A2 × chinook/sakila 两组 run
- [ ] 首轮正确率 / 修复增益指标

## A1(k6) vs A2 对比
| 数据集 | A1 EX | A2 EX | A2 首轮正确率 | 修复增益 | escalate 次数 | ¥/题 |
| --- | --- | --- | --- | --- | --- | --- |

## 三个结论
1. 修复增益来自哪类失败（escalate 修检索错 vs repair 修语法错，各 n=?）
2. 意外收获或负结果（行为正确率？某题变差？）
3. 修复环修不了的失败还剩什么（→ Day 4 verifier 的靶子清单）

## 明天（Day 4）第一件事
```

---

## 10. 验收清单

- [ ] `pytest -q` 全绿（diagnoser 分类单测无 LLM 依赖）
- [ ] meta.json 里有 `eval_config` 与含配置的新指纹
- [ ] A2 的首次生成 SYSTEM 是 `from a0 import SYSTEM`
- [ ] escalate 每题最多 1 次，attempts 硬上限 3（看记录里没有 attempts=4 的题）
- [ ] results.jsonl 里每题有 attempts / escalated / ex_first / diagnosis
- [ ] 能当场演示一道"失败 → 修复 → 成功"题的完整 sql_history
- [ ] 日报有修复增益数字，且能说明它来自哪类失败

---

## 11. 五个坑

1. **attempts 没人加 / 加了但路由没查** → 无限循环烧钱。单测里构造一个永远失败的假状态验证终止。
2. **escalate 后不记录标志** → 消融变量污染，A2 的增益说不清来自修复还是检索。`escalated` 必须进记录。
3. **空结果一律判可疑** → 正确空结果（"不存在 X"类题）被误修，每题还多烧一次 LLM 调用。LLM 判断那一步不能省。
4. **指纹升级后重跑旧 run_id** → 指纹不匹配全部重跑扣费。旧 run 封存。
5. **为了"修复环有用"偷偷把 A2 的首次生成 prompt 改好** → A2 − A1 的差异必须是且仅是"有没有第二次机会"。

---

## 12. 给 Day 4 的接口约定

| 今天的产物 | Day 4 怎么用 |
| --- | --- |
| `diagnosis.category` | verifier 的"结果错但无报错"（如 sa-014）是新类别 `result_suspect`，进同一 diagnoser 框架 |
| `behavior` 字段的 refuse 路径 | clarifier 加入后增加 `clarify` 取值，HITL interrupt 复用 checkpointer |
| `ex_first` / `repair_gain` | A3 报告加"双路校验拦截率"，与修复增益并列 |
| compose lite 版 | 换成真正的 answer_composer：结论只能引用执行结果 |
