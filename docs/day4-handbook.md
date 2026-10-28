# DataPilot Day 4 实施手册 —— 校验与行为决策（A3）

> 输入状态：A2 双库已跑通（v3），修复增益在 sakila 兑现（+5.56pt，sa-015）。
> 今天的目标：解决 Day 3 数据暴露的三类 A2 修不了的失败。
> 预计 7–8 小时。所有代码块已核对过当前仓库的真实 API（langgraph 1.2.16 /
> checkpoint-sqlite 3.1.2 / LLMClient.chat_json / results_equal），可直接照抄。

## 0. 今天全部工作的出发点（15 分钟，先读懂）

Day 3 v3 的失败解剖，三条结论对应今天的三个新组件：

| Day 3 证据 | 失败模式 | 今天的对策 |
| --- | --- | --- |
| ch-021/022、sa-013/014：rows>0、diag=None、ex=False | **非空错结果**——执行成功但答错，diagnose 看不到 | verifier |
| behavior_ok=0，ch-027 被 escalate 白烧一轮 | **歧义题被硬答**——该反问的没反问 | gate（clarify） |
| ch-030 编造 USA 归一化、ch-008 交 `WHERE 1=0` | **对抗题被编造答案**——该拒答的没拒答 | gate（refuse） |

一句话：A2 的修复环回答"SQL 错了怎么办"，A3 要回答"**这题该不该答、答案可不可信**"。

### 公平性红线（同前两天）

- A3 = A2（top_k=6、修复环、escalate 全部冻结）+ gate + verifier + composer。**唯一自变量是新增组件**。
- generate 的 SYSTEM prompt 逐字节不变。
- A2 的图拓扑不许改——`build_graph` 加 `with_reliability` 开关，A2 run 走原拓扑（见第 6 节）。
- 改完先跑冒烟再开全量。

## 1. A3 图结构总览

```
                                                ┌─ 报错/空结果 → diagnose（A2 原逻辑）
START → retrieve → gate ──answer──→ generate → validate → execute ┤
                    │                                           └─ ok 且有行 → verify ──pass──→ compose
                    ├─clarify→ [hitl ? clarify_wait : compose]           │
                    └─refuse→ compose                                    └─wrong─┬─ 未打回过 → diagnose
                                                                                 └─ 已打回过 → compose（认栽，防震荡）
clarify_wait ──用户回答──→ retrieve（带澄清后的问题重走）
```

两处新增决策点都用 **fail-open 默认**：gate 异常按 answer 放行、verifier 异常按 pass 放行。
理由相同：误杀一道 answer 题 = EX 直接掉 4–5pt；漏判只是维持 A2 现状。代价不对称，默认必须保守。

## 2. state.py 增量

追加到 `AgentState` 末尾（原有字段一个不动）：

```python
    # —— Day 4 新增 ——
    difficulty: int            # 题目难度，verifier 的 LLM judge 按它控制成本
    hitl: bool                 # True 时 clarify 走 interrupt 等人答（仅 CLI 演示链路）
    gate: Optional[dict]       # node_gate{action, reason, clarifying_question}
    verify: Optional[dict]     # node_verifier{verdict, reason, flags}
    verify_retried: bool       # verify 打回后已修复过一次（防 verify↔repair 震荡）
    answer_text: Optional[str] # compose 产出的人话结论
```

## 3. gate `src/datapilot/nodes/gate.py`（新建，1.5 小时）

位置：retrieve 后、generate 前。判断"可不可答"必须看到检索结果（裸看问题判断不了
"库中没有删除时间戳列"这类对抗题）；放行前不生成 SQL（歧义题不该白烧生成 token）。

```python
# gate：行为决策前置。只判"该不该答"，不生成 SQL。
# 设计纪律：fail-open——任何异常都按 answer 放行，误杀比漏判代价大。

import json

from src.datapilot.config import settings
from src.datapilot.llm.client import LLMClient
from src.datapilot.state import AgentState
from src.datapilot.tools.schema import table_units

GATE_SYSTEM = "你是数据库问答的行为裁判。只输出严格 JSON。"

# 【方案 A · 实测修正】refuse 判定必须依据全库表清单，不能依据检索结果。
# 事故复盘：demo 中"哪个歌单最受欢迎？"的检索结果漏了 Playlist（中英映射盲区，
# BM25 无跨语言能力），gate 对部分 schema 判"Schema 中没有 Playlist 实体"→ 误拒。
# "检索到的表里没有" ≠ "全库没有"——refuse 决策需要完备性知识。
GATE_USER = """# 全库表清单（该数据库拥有的全部表及列，判 refuse 的唯一依据）
{catalog}

# 检索到的相关表 Schema（供判断 answer/clarify 参考，可能不全）
{schema}

# 用户问题
{question}

判断该问题的行为类别：
- "answer"：问题明确、且所需信息在全库表清单中存在
- "clarify"：问题有歧义（关键概念未定义口径，如"最受欢迎""最活跃"），必须反问才能给出唯一正确答案
- "refuse"：【仅当】问题引用的实体/列/业务概念在【全库表清单】中也不存在，
  或要求的信息从根本上无法由该库回答。
  注意：检索到的相关表不全不构成 refuse 理由——实体在全库清单里存在但检索结果
  中没有时，应判 answer（后续流程会自动扩大检索）。

只输出 JSON：{{"action": "answer|clarify|refuse", "reason": "一句话",
"clarifying_question": "若 clarify 给出反问句，否则为空字符串"}}"""

_VALID_ACTIONS = ("answer", "clarify", "refuse")


def _full_catalog(db_id: str) -> str:
    """全库表名紧凑清单：每张表一行 'TableName(col1, col2, ...)'，约 200 token。
    加载失败遵循 fail-open 纪律：降级为空清单而不是让 gate 崩溃。"""
    try:
        db = settings.db_dir / f"{db_id}.db"
        lines = []
        for u in table_units(db):
            cols = ", ".join(c["name"] for c in u["columns"])
            lines.append(f"{u['table']}({cols})")
        return "\n".join(lines)
    except Exception:
        return "(全库清单加载失败——无法判 refuse，请倾向 answer/clarify)"


def node_gate(state: AgentState, client: LLMClient) -> dict:
    # 调用 client.chat_json(system, user)，返回 LLMResult：
    # {text, model, in_tokens, out_tokens, cost_cny, latency_ms}
    # 其中 text = {"action": "answer|clarify|refuse", "reason": "...", "clarifying_question": "..."}
    r = client.chat_json(GATE_SYSTEM, GATE_USER.format(
        catalog=_full_catalog(state.get("db_id") or ""),
        schema=state["schema_text"], question=state["question"]))
    # 累加字段（llm_calls/cost_cny/in_tokens 挂 operator.add Reducer，直接返回增量即可）
    out = {"llm_calls": 1, "cost_cny": r.cost_cny, "in_tokens": r.in_tokens}
    try:
        verdict = json.loads(r.text)
        action = verdict.get("action", "answer")
        if action not in _VALID_ACTIONS:
            action = "answer"  # 非法 action 一律放行
    except Exception:
        action, verdict = "answer", {"reason": "gate 输出解析失败，默认放行"}
    out["gate"] = {
        "action": action,
        "reason": verdict.get("reason", ""),
        "clarifying_question": verdict.get("clarifying_question", ""),
    }
    if action != "answer":
        out["behavior"] = action
    return out
```

clarify_wait **必须独占一个节点**：langgraph 1.x 里 resume 时节点从头重跑，
若 interrupt 和 LLM 调用同处一个节点，那次 LLM 调用会重复扣费且结果可能漂移。

```python
# —— 追加在 gate.py 末尾 ——

from langgraph.types import interrupt  # langgraph 1.2 写法：from langgraph.types


def node_clarify_wait(state: AgentState) -> dict:
    """HITL 专用：挂起等人答。评测链路不会进入这里（hitl=False 时 gate 直连 compose）。"""
    g = state.get("gate") or {}
    reply = interrupt({"clarifying_question": g.get("clarifying_question") or "请补充说明"})
    # resume 后从这里继续，reply 即用户回答；把澄清并入问题，gate 标记放行
    return {
        "question": f"{state['question']}（用户澄清：{reply}）",
        "gate": {"action": "answer", "reason": "用户已澄清"},
    }
```

单测 `tests/test_gate.py`（新建）：

```python
from src.datapilot.nodes.gate import node_gate


class _Resp:
    def __init__(self, text):
        self.text = text
        self.cost_cny = 0.001
        self.in_tokens = 100


class _FakeClient:
    def __init__(self, text):
        self._text = text

    def chat_json(self, system, user):
        return _Resp(self._text)


def _state():
    # db_id 必须给真实库：方案 A 后 gate 会读全库表清单（_full_catalog）。
    # 这里走真实 chinook 反而更好——顺带覆盖了目录加载路径。
    return {"question": "q", "db_id": "chinook", "schema_text": "CREATE TABLE T(id INT);"}


def test_gate_fail_open_on_bad_json():
    out = node_gate(_state(), _FakeClient("这不是JSON"))
    assert out["gate"]["action"] == "answer"
    assert "behavior" not in out  # 放行时不许动 behavior


def test_gate_fail_open_on_unknown_action():
    out = node_gate(_state(), _FakeClient('{"action": "maybe", "reason": "x"}'))
    assert out["gate"]["action"] == "answer"


def test_gate_clarify_sets_behavior():
    out = node_gate(_state(), _FakeClient(
        '{"action": "clarify", "reason": "口径未定义", "clarifying_question": "按销量还是评分？"}'))
    assert out["behavior"] == "clarify"
    assert out["gate"]["clarifying_question"] == "按销量还是评分？"


def test_gate_refuse_sets_behavior():
    out = node_gate(_state(), _FakeClient(
        '{"action": "refuse", "reason": "库中无该列", "clarifying_question": ""}'))
    assert out["behavior"] == "refuse"
```

## 4. verifier `src/datapilot/nodes/verifier.py`（新建，2 小时）

**为什么不用总手册原案的"第二路径独立生成 + 结果比对"**：Day 3 的失败全是**系统性错误**
（词形、中英映射、语义误读），不是随机抖动——双路径大概率犯同样的错，比对不出来，
还白付 2× 生成成本。双路径抓"随机幻觉"，抓不了"一致性误解"。刻意偏离，日报写明理由。

两层结构：**确定性检查零成本先跑，LLM judge 只在有告警或高难度题时启用**（控制成本）。

```python
# verifier：拦截"非空错结果"——执行成功但答案不可信。
# 职责红线：只判不改。verdict=wrong 打回 diagnose，修 SQL 是 repairer 的事。

import json

from src.datapilot.llm.client import LLMClient
from src.datapilot.state import AgentState

VERIFY_SYSTEM = "你是苛刻的 SQL 结果评审。只输出严格 JSON。"

VERIFY_USER = """# 用户问题
{question}

# 生成的 SQL
{sql}

# 执行结果（共 {n_rows} 行，前 5 行）
{sample}

# 确定性检查告警
{flags}

逐项核对：① SELECT 的列是否回答了问题所问 ② WHERE/JOIN 与题面约束是否一致
③ 聚合粒度是否正确 ④ 结果行数/取值是否与题面预期矛盾。
拿不准就 pass——只拦截有明确证据的错误。
只输出 JSON：{{"verdict": "pass|wrong", "reason": "一句话"}}"""


def deterministic_flags(rows, columns, truncated) -> list[str]:
    """零成本的客观异常检测。纯函数、不依赖 state，方便单测。"""
    flags = []
    if truncated:
        flags.append("结果撞 max_rows 截断，可能不完整")
    if rows:
        if all(all(v is None for v in row) for row in rows):
            flags.append("所有行的所有列全为 NULL")
        elif columns:
            # 整列全 NULL：典型的 join 条件错误或列选错（Day 3 的 ch-021 就是这形态）
            null_cols = [c for i, c in enumerate(columns)
                         if all(row[i] is None for row in rows)]
            if null_cols:
                flags.append(f"整列全 NULL：{null_cols}")
    return flags


def node_verify(state: AgentState, client: LLMClient) -> dict:
    flags = deterministic_flags(
        state.get("rows"), state.get("columns"), state.get("truncated"))
    # 成本控制：无告警且低难度 → 免 LLM 直接 pass（不调 LLM 就不许返回累加字段）
    if not flags and (state.get("difficulty") or 1) < 3:
        return {"verify": {"verdict": "pass", "reason": "确定性检查通过，低难度免判",
                           "flags": []}}

    rows = state.get("rows") or []
    sample = "\n".join(str(tuple(r)) for r in rows[:5])
    # 调用 client.chat_json，返回 LLMResult：{text, model, in_tokens, out_tokens, cost_cny, latency_ms}
    # 其中 text = {"verdict": "pass|wrong", "reason": "一句话"}
    r = client.chat_json(VERIFY_SYSTEM, VERIFY_USER.format(
        question=state["question"], sql=state["sql"],
        n_rows=len(rows), sample=sample or "（空）",
        flags="；".join(flags) or "无"
    ))
    out = {"llm_calls": 1, "cost_cny": r.cost_cny, "in_tokens": r.in_tokens}
    try:
        v = json.loads(r.text)
        verdict = v.get("verdict", "pass")
        if verdict not in ("pass", "wrong"):
            verdict = "pass"  # fail-open，同 gate
    except Exception:
        verdict, v = "pass", {"reason": "verify 输出解析失败，默认放行"}
    out["verify"] = {"verdict": verdict, "reason": v.get("reason", ""), "flags": flags}
    return out
```

单测 `tests/test_verifier.py`（新建）：

```python
from src.datapilot.nodes.verifier import deterministic_flags, node_verify


def test_flags_all_null_rows():
    assert deterministic_flags([(None, None)], ["a", "b"], False)


def test_flags_null_column():
    flags = deterministic_flags([(1, None), (2, None)], ["id", "x"], False)
    assert any("整列全 NULL" in f for f in flags)


def test_flags_truncated():
    assert deterministic_flags([(1,)], ["a"], True)


def test_flags_clean():
    assert deterministic_flags([(1, "a"), (2, "b")], ["id", "name"], False) == []


class _Resp:
    text = '{"verdict": "wrong", "reason": "SELECT 列与问题不符"}'
    cost_cny = 0.001
    in_tokens = 100


class _FakeClient:
    def chat_json(self, system, user):
        return _Resp()


def test_verify_skips_llm_on_easy_clean():
    out = node_verify({"rows": [(1,)], "columns": ["a"], "truncated": False,
                       "difficulty": 1, "question": "q", "sql": "SELECT 1"},
                      _FakeClient())
    assert out["verify"]["verdict"] == "pass"
    assert "llm_calls" not in out  # 没调 LLM 就不许返回累加字段（否则多计）


def test_verify_calls_llm_on_flags():
    out = node_verify({"rows": [(None,)], "columns": ["a"], "truncated": False,
                       "difficulty": 1, "question": "q", "sql": "SELECT 1"},
                      _FakeClient())
    assert out["verify"]["verdict"] == "wrong"
    assert out["llm_calls"] == 1


def test_verify_fail_open_on_bad_json():
    class _BadClient:
        def chat_json(self, system, user):
            r = _Resp()
            r.text = " garbage "
            return r
    out = node_verify({"rows": [(None,)], "columns": ["a"], "truncated": False,
                       "difficulty": 3, "question": "q", "sql": "SELECT 1"},
                      _BadClient())
    assert out["verify"]["verdict"] == "pass"
```

## 5. compose / give_up 升级 `nodes/terminal_nodes.py`（整体替换，30 分钟）

composer 用**规则拼装，不调 LLM**：Day 4 每题已多 gate（+verify）最多两次调用，
结论润色再调一次 LLM 成本就失控了。规则版同样满足"结论只能引用执行结果"。

```python
# give_up 与 compose（Day 4 版：产出 answer_text）

from src.datapilot.state import AgentState


def node_give_up(state: AgentState) -> dict:
    d = state.get("diagnosis") or {}
    reason = d.get("reason") or "unknown"
    out = {"give_up_reason": reason, "rows": None,
           "answer_text": f"无法回答：{reason}"}
    # 危险 SQL 被拦截 → 这是正确的拒答行为，不是失败
    if d.get("category") == "unsafe":
        out["behavior"] = "refuse"
    return out


def node_compose(state: AgentState) -> dict:
    """产出 answer_text。规则拼装不调 LLM（成本纪律）。"""
    g = state.get("gate") or {}
    if state.get("behavior") == "clarify":
        return {"answer_text": f"需要澄清：{g.get('clarifying_question') or '请补充口径'}"}
    if state.get("behavior") == "refuse":
        return {"answer_text": f"无法回答：{g.get('reason') or '问题超出本数据库范围'}"}

    rows = state.get("rows")
    if not rows:
        return {"answer_text": "未查询到符合条件的数据。"}
    header = " | ".join(str(c) for c in (state.get("columns") or []))
    body = "\n".join(" | ".join(str(v) for v in row) for row in rows[:10])
    suffix = "（结果已截断）" if state.get("truncated") else ""
    return {"answer_text": f"查询结果（{len(rows)} 行）{suffix}：\n{header}\n{body}"}
```

## 6. graph.py 改造（45 分钟）

`build_graph` 加 `with_reliability` 开关。**A2 拓扑保持原样**（`with_reliability=False`
时走原来的边），旧 run 的可比性不受影响：

```python
# A2 的图。checkpointer 的 thread_id 用 f"{run_id}:{question_id}"——
# 跨 run 复用同一 checkpoints.db 时旧 state 会污染新 run。
import sqlite3  # 【改】新版 SqliteSaver.from_conn_string 返回上下文管理器，需手动建连接

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import StateGraph, START, END

# settings / _client / _retrievers 各产生两份实例）
from src.datapilot.llm.client import LLMClient
from src.datapilot.nodes.common_nodes import node_retrieve, node_generate, node_validate, node_execute
from src.datapilot.nodes.diagnoser import node_diagnose
from src.datapilot.nodes.repairer import node_repair
from src.datapilot.nodes.terminal_nodes import node_compose, node_give_up
from src.datapilot.state import AgentState

# A3
from src.datapilot.nodes.gate import node_gate, node_clarify_wait
from src.datapilot.nodes.verifier import node_verify

_client: LLMClient | None = None


def _get_client() -> LLMClient:
    global _client
    if _client is None:
        _client = LLMClient()
    return _client


def build_graph(checkpoint_db: str, with_reliability: bool = False):
    g = StateGraph(AgentState)
    g.add_node("retrieve", node_retrieve)
    g.add_node("generate", lambda s: node_generate(s, _get_client()))
    g.add_node("validate", node_validate)
    g.add_node("execute", node_execute)
    g.add_node("diagnose", lambda s: node_diagnose(s, _get_client()))
    g.add_node("repair", lambda s: node_repair(s, _get_client()))
    g.add_node("give_up", node_give_up)
    g.add_node("compose", node_compose)

    if with_reliability:
        # —— A3：gate + verify 接入 ——
        g.add_node("gate", lambda s: node_gate(s, _get_client()))
        g.add_node("clarify_wait", node_clarify_wait)
        g.add_node("verify", lambda s: node_verify(s, _get_client()))

        g.add_edge(START, "retrieve")
        g.add_edge("retrieve", "gate")
        g.add_conditional_edges("gate", _route_after_gate,
            {"generate": "generate", "clarify_wait": "clarify_wait", "compose": "compose"})
        g.add_edge("clarify_wait", "retrieve")  # 用户澄清后带新问题重走检索
    else:
        # —— A2 原拓扑，不动 ——
        g.add_edge(START, "retrieve")
        g.add_edge("retrieve", "generate")

    # —— A2 原拓扑，不动 ——
    g.add_conditional_edges("generate",
        lambda s: "validate" if s.get("sql") else "diagnose",
        {"validate": "validate", "diagnose": "diagnose"})
    g.add_conditional_edges("validate",
        lambda s: "execute" if not s.get("error") else "diagnose",
        {"execute": "execute", "diagnose": "diagnose"})

    if with_reliability:
        g.add_conditional_edges("execute", _route_after_execute_reliability,
            {"verify": "verify", "diagnose": "diagnose"})
        g.add_conditional_edges("verify", _route_after_verify,
            {"compose": "compose", "diagnose": "diagnose"})
    else:
        # 【改】execute 的条件边必须放进 else——原来 if 块内外各注册了一次，
        # 同一源节点重复注册 Branch 会在 compile 时抛 ValueError，A2 也跑不了
        g.add_conditional_edges("execute", _route_after_execute,
            {"compose": "compose", "diagnose": "diagnose"})

    g.add_conditional_edges("diagnose", _route_after_diagnose,
        {"repair": "repair", "escalate": "retrieve", "accept": "compose", "give_up": "give_up"})
    g.add_edge("repair", "validate")
    g.add_edge("give_up", "compose")
    g.add_edge("compose", END)

    # 【改两处】
    # 将LangGraph 图的执行状态 检查点checkpointer 持久化存储到sqlite 数据库中
    # 1) 当前版本的 SqliteSaver.from_conn_string() 返回的是上下文管理器（contextlib._GeneratorContextManager），
    #    不是 saver 实例——不进入 with 就拿不到真正的 checkpointer。改为手动建连接直接构造。
    #    check_same_thread=False 是必须的：作用是解除 SQLite 默认的线程限制（LangGraph 可能在别的线程里执行节点。）
    # 2) compile 的 kwarg 是 checkpointer=，不是 checkpoint_db=。
    # 注意：在 SQLite 里，传入的字符串就是数据库文件的路径。sqlite3.connect() 会把它当作一个文件系统路径去打开（或自动创建）对应的数据库文件。
    conn = sqlite3.connect(checkpoint_db, check_same_thread=False)
    cp = SqliteSaver(conn)
    return g.compile(checkpointer=cp)


def _route_after_gate(s: AgentState) -> str:
    action = (s.get("gate") or {}).get("action", "answer")
    if action == "clarify":
        return "clarify_wait" if s.get("hitl") else "compose"
    if action == "refuse":
        return "compose"
    return "generate"


def _route_after_execute_reliability(s: AgentState) -> str:
    if s["exec_ok"] and s.get("rows"):
        return "verify"   # 成功且有行 → 校验
    return "diagnose"     # 报错或空结果 → 诊断（A2 原路径）


def _route_after_verify(s: AgentState) -> str:
    verdict = (s.get("verify") or {}).get("verdict", "pass")
    if verdict == "wrong" and not s.get("verify_retried"):
        return "diagnose"  # 打回修复，仅限一次
    return "compose"       # pass；或已打回过一次 → 认栽接受现状，防震荡


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

**diagnose 的补丁**（`nodes/diagnoser.py`，改三处，不是新建）：

```python
    # ⓪ category 判定：verify 打回的情况优先判断（此时 err=None、rows 非空，
    #    空结果分支和 classify_error 都不会命中，不加这支就会落进 "other"）
    if (state.get("verify") or {}).get("verdict") == "wrong":
        category = "wrong_result"
    elif not err and state.get("exec_ok") and not state.get("rows"):
        ...（原空结果分支不变）
    else:
        category = classify_error(err or "", state.get("error_code"))

    # ① 动作决策的 if 链最前面加一支：
    if category == "wrong_result":
        action, reason = "repair", "verifier 判定结果与问题不符，打回修复"
    elif category == "unsafe":
        ...（原逻辑不变）

    # ② 返回处（out dict 组装完、"if action == escalate" 附近）加：
    if category == "wrong_result":
        out["verify_retried"] = True   # 打回只许一次，防 verify↔repair 震荡
```

注意：wrong_result **不走 escalate**——verifier 是在当前 schema 下判的，结果错了先修 SQL；
schema 怀疑仍由 schema_incomplete / empty_suspicious 通道负责。

## 7. pipeline 与配置（20 分钟）

`eval/configs/a3.yaml`（新建）：

```yaml
pipeline: a3
top_k: 6
repair_max_attempts: 3
```

`src/datapilot/pipelines/a3.py`（新建，与 a2 的差异只有三处，用 ★ 标出）：

```python
# A3 = A2 + gate + verifier + composer。与 a2.py 的差异处用 ★ 标出。

import threading
import time
import uuid

from src.datapilot.graph import build_graph


def graph_answer_a3(q: dict, client=None, cfg: dict | None = None) -> dict:
    cfg = cfg or {}
    t0 = time.perf_counter()
    # ★1 打开可靠性组件；checkpoint 仍按线程隔离（Day 3 的并发锁教训）
    app = build_graph(f"checkpoints-{threading.get_ident()}.db",
                      with_reliability=True)
    final = app.invoke(
        {
            "question": q["question"], "db_id": q["db_id"],
            "trace_id": f"a3-{q['id']}",
            "top_k": cfg.get("top_k", 6),
            "max_attempts": cfg.get("repair_max_attempts", 3),
            "difficulty": q.get("difficulty", 1),  # ★2 verifier 成本门控用
            "hitl": False,                          # ★2 评测链路不挂起
            "attempts": 0, "escalated": False, "sql_history": [],
            "verify_retried": False,
            "behavior": "answer", "cost_cny": 0.0, "in_tokens": 0, "llm_calls": 0,
        },
        # thread_id 带 uuid：防同题重跑时旧 checkpoint 状态泄漏（Day 3 教训）
        config={"configurable": {"thread_id": f"a3:{q['id']}:{uuid.uuid4().hex[:8]}"}},
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
            "first_rows": final.get("first_rows"),  # runner 算完 ex_first 后会丢掉
            "diagnosis": final.get("diagnosis"),
            "error_code": final.get("error_code"),
            "gate": final.get("gate"),      # ★3 行为决策留痕（进 results.jsonl 可溯源）
            "verify": final.get("verify"),  # ★3 校验留痕
        },
    }
```

`eval/runner.py` 的 `get_pipeline` 加分支（Day 3 起该函数已从 cli.py 移到 runner.py，别找错文件）：

```python
    if name == "a3":
        from src.datapilot.pipelines.a3 import graph_answer_a3
        return lambda q: graph_answer_a3(q, cfg=cfg)
```

## 8. 还指纹债（15 分钟）

`runner.py` 的 `prompt_fingerprint()` 改为汇总全部进图的 prompt：

```python
def prompt_fingerprint() -> str:
    """所有进入图里的 prompt 都进指纹——改任何一个都视为不可比的新实验。"""
    try:
        from src.datapilot.pipelines import a0
        from src.datapilot.nodes import diagnoser, gate, repairer, verifier
        parts = [a0.SYSTEM, repairer.REPAIR_SYSTEM, diagnoser.EMPTY_JUDGE,
                 gate.GATE_SYSTEM, verifier.VERIFY_SYSTEM]
        return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()[:12]
    except Exception:
        return "na"
```

⚠️ 两个后果要写进日报：① 改完所有旧 run_id 不可续跑（指纹不匹配会 raise）——
A3 本来就用新 run_id，无影响；② a0–a2 旧报告页眉里的指纹值与新算法产出对不上，
属于算法升级而非数据污染。

## 9. metrics / report 新指标（45 分钟）

`metrics.py` 的 `aggregate` 返回 dict 里追加四个指标：

```python
        # —— Day 4：gate 与 verifier 的功过账 ——
        # gate 误杀：可答题被拦成 clarify/refuse（每道都是 EX 的直接损失）
        "gate_false_kill": sum(
            1 for r in answerable if r.get("behavior") not in (None, "answer")),
        # verify 触发数（answer 题中 verify 留痕的）
        "n_verified": sum(1 for r in answerable if r.get("verify")),
        # verify 的功：判 wrong 且最终从错修对（escalate 修复的题没有 verify 留痕，天然排除）
        "verify_fixed": sum(
            1 for r in answerable
            if (r.get("verify") or {}).get("verdict") == "wrong"
            and r.get("ex_first") is False and r.get("ex") is True),
        # verify 的过：首轮对、终轮错。A3 链路里首轮成功后唯一能改变结果的
        # 路径就是 verify 打回 → repair 改错，所以这就是误杀数
        "verify_false_alarm": sum(
            1 for r in answerable
            if r.get("ex_first") is True and r.get("ex") is False),
```

`report.py` 汇总表照现有格式追加这四行，并加**行为混淆矩阵**小节
（`behavior_ok` 一个数看不出 gate 在哪类题上犯晕）：

```python
def behavior_matrix(records: list[dict]) -> str:
    """行=期望行为，列=实际行为。"""
    from collections import Counter
    cnt = Counter((r["expected_behavior"], r.get("behavior") or "?") for r in records)
    behaviors = sorted({b for _, b in cnt})
    lines = ["| 期望 \\ 实际 | " + " | ".join(behaviors) + " |",
             "|" + " --- |" * (len(behaviors) + 1)]
    for exp in ("answer", "clarify", "refuse"):
        row = [str(cnt.get((exp, b), 0)) for b in behaviors]
        lines.append(f"| {exp} | " + " | ".join(row) + " |")
    return "\n".join(lines)
```

在 `write_report` 里找个合适位置调用并把结果拼进报告（"## 汇总"之后加 "## 行为矩阵"）。

## 10. HITL 演示：interrupt() 接入 `ask`（1 小时）

评测链路里 clarify 直接 compose（没有真人），HITL 是**演示链路**，两者共存。
总手册验收要求"现场演示：提问 → Agent 反问 → 你回答 → 继续执行"。

`cli.py` 的 `ask` 命令整体替换：

```python
@app.command("ask")
def cmd_ask(question: str = "", db: str = "chinook",
            thread: str = "cli-default", resume: str = ""):
    """单题即席提问，支持 HITL 澄清：
    ask "哪个歌单最受欢迎？" --thread demo1
    ask --thread demo1 --resume "按购买次数"
    """
    from langgraph.types import Command
    from src.datapilot.graph import build_graph

    # ★ 固定 checkpoint 文件：评测那套 per-thread 文件（checkpoints-{线程id}.db）
    # 跨进程 resume 时找不到旧 checkpoint——演示链路必须用固定文件名
    app = build_graph("checkpoints-cli.db", with_reliability=True)
    cfg = {"configurable": {"thread_id": thread}}
    if resume:
        # langgraph 1.x：Command(resume=...) 把用户回答送回挂起的 interrupt 处
        final = app.invoke(Command(resume=resume), config=cfg)
    else:
        final = app.invoke(
            {"question": question, "db_id": db, "trace_id": f"ask-{thread}",
             "top_k": 6, "max_attempts": 3, "difficulty": 3,
             "hitl": True,   # ★ 演示链路：clarify 走 interrupt 挂起等人答
             "attempts": 0, "escalated": False, "sql_history": [],
             "verify_retried": False,
             "behavior": "answer", "cost_cny": 0.0, "in_tokens": 0, "llm_calls": 0},
            config=cfg)

    # langgraph 1.x：被 interrupt 挂起时，结果 dict 里带 __interrupt__ 键
    interrupts = final.get("__interrupt__")
    if interrupts:
        rprint(f"[yellow]Agent 反问：{interrupts[0].value['clarifying_question']}[/yellow]")
        rprint(f'继续：ask --thread {thread} --resume "你的回答"')
        return
    rprint(final.get("answer_text"))
    rprint(f"SQL: {final.get('sql')}")
    rprint(f"(llm_calls={final.get('llm_calls')}, cost=¥{final.get('cost_cny', 0):.4f})")
```

演示脚本（写进 README demo 章节，面试现场用）：

```bash
python -m src.datapilot.cli ask --question "哪个歌单最受欢迎？" --thread demo1
# → Agent 反问："受欢迎"指播放量、收藏数还是购买次数？
python -m src.datapilot.cli ask --thread demo1 --resume "按购买次数"
# → 带澄清后的查询结果
```

**实测记录（方案 A 落地后，2026-10-27）**：

- 第一跳符合预期：gate 判 clarify → interrupt 挂起 → 打印反问。
- ⚠️ **方案 A 修复前**：这道题曾被 gate 误拒（"Schema 中没有 Playlist 实体"）——
  根因是检索漏表（中文"歌单"召不回 Playlist，BM25 中英映射盲区），gate 拿部分
  schema 做 refuse 决策把检索失败放大成误拒。这正是 `_full_catalog` 存在的原因。
- ⚠️ **已知残留**：resume 后带澄清问题重走检索，"歌单"**仍然**召不回 Playlist，
  生成的 SQL 可能落到 Album 等错误表上——且结果非空，escalate 无触发信号，
  verifier 是最后一道防线但检索不修它也无力回天。**面试演示时建议换一道
  检索能命中的歧义题**（如"最活跃的客户"——Customer/Invoice 词面可匹配），
  把这道题留给"已知局限"章节讲：它是 Day 5 向量检索/同义词典立项的直接证据。

## 11. 实验与解读（1.5 小时）

```bash
# 冒烟：先看行为对不对，不看 EX
python -m src.datapilot.cli eval --config a3 --limit 6 --run-id a3_smoke
# 逐条看 results.jsonl 里的 gate 字段：clarify/refuse 题有没有被正确拦住

# 全量
python -m src.datapilot.cli eval --config a3 --run-id a3_chinook
python -m src.datapilot.cli eval --config a3 --dataset data/benchmarks/sakila_v0.jsonl --run-id a3_sakila
```

### 解读规则（数字出来对号入座）

- **behavior_ok 从 0 涨上来** → gate 起效。同时盯 `gate_false_kill`：>1 → GATE_USER 太激进，先调 prompt 再认数字。
- **sakila EX 在 88.89% 基础上再涨** → verifier 拦到了非空错结果，看 `verify_fixed` 归因。
- **EX 反而降** → 查 `verify_false_alarm`。≥2 → verifier 太激进，把 LLM judge 收紧为"只在 flags 非空时启用"（去掉 difficulty>=3 的触发）。
- **chinook EX 跌破 91.67%** → 大概率 gate/verify 误伤，逐题看 `gate`/`verify` 留痕，不许认账。
- **单题成本涨到约 2–3 倍** → 正常：gate + verify 各一次调用。成本叙事从"A1 省 token"升级为"A3 用 X 分钱/题买行为正确率和结果可信度"——这是日报成本章节的写法。

## 12. 验收清单

- [ ] test_gate.py（4 个）+ test_verifier.py（7 个）全绿，全量 pytest 绿
- [ ] a3_smoke 逐条看 gate 留痕：特殊题拦截符合预期
- [ ] 行为混淆矩阵：chinook 6 道特殊题 ≥4 道行为正确
- [ ] `verify_fixed` ≥ 1 且 `verify_false_alarm` ≤ 1
- [ ] `gate_false_kill` ≤ 1
- [ ] HITL 演示跑通（interrupt → resume 全链路）
- [ ] A1/A2/A3 × 双库六组数字同表对比，全部可溯源 run_id
- [ ] 日报：对比表、混淆矩阵、verify 功过账、成本变化、双路径弃用理由

## 13. 常见坑（今天专属）

1. **gate 放 generate 后** → 白烧生成 token，且"该不该答"的决策被 SQL 草稿污染。
2. **interrupt 与 LLM 调用同节点** → resume 时节点从头重跑，LLM 调用重复扣费还可能漂移。
3. **verifier 直接改 SQL** → 职责混乱，verify_fixed 归因失效。
4. **LLM judge 全题启用** → 成本失控。flags + difficulty 前置过滤。
5. **verify↔repair 无次数上限** → 震荡到 attempts 耗尽。verify_retried 只许一次。
6. **HITL 用 per-thread checkpoint 文件** → resume 换进程后找不到 checkpoint。
7. **gate/verify 不是 fail-open** → 一个解析异常就连锁掉 EX。默认必须放行。
8. **compose 调 LLM 润色** → 每题三次调用起步，成本叙事崩掉。规则拼装够用。
