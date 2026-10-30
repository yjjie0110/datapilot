# Day 6 实施手册 — 结论生成 + verifier 降级 + 可观测 + 工程化

> 前置：Day 5 已收口（15 个 run 全部落盘、消融矩阵出数字、gate 收紧归零）。
> 本手册代码块已按项目实际导入约定（`from src.datapilot.*`）核对。
> **纪律提醒：今天动 prompt / 组件后必须用新 run_id 重跑，禁止续跑旧 run_id。**

## 0. 今天为什么是这三件事（10 分钟）

Day 5 收尾时留下**两笔没还的债**，它们会直接影响 Day 7 的"表达"质量，必须先清：

1. **"错误自信率"抽评名存实亡。** `node_compose` 产出的 `answer_text` 是"结果集前 10 行直接 dump"，不是自然语言结论——它永远不会产生"相关当因果""样本当全体"这类断言，所以 review_sheet 抽出来的 30 条根本没有可勾的"结论文本"。**结论：你的 Agent 现在还不会"说话"，只会"吐表"。** 这是比 EX 更该补的能力缺口——数据分析 Agent 的最终产物是"结论"，不是 SQL。

2. **verifier 的存废悬而未决。** 三库 `verify_fixed` 全 0，按 Day 5 手册 §3 决策树：错误自信样本 < 5 题，**不许下"有效/无效"的结论**，只能执行"降级"——砍掉 LLM judge，只留 `deterministic_flags` 做零成本 guard。省掉全部 verify 的 token（实测 A3 单题 ¥0.0065，其中相当一部分是 verify 的 LLM 调用）。

3. **然后才是总手册 Day 6 的既定主线**：可观测（tracer）+ Demo（Streamlit）+ 工程化（Docker）。这三件事是"让项目能在一台干净机器上跑起来、能现场演示、能讲清调用链"的收尾。

> 一句话：Day 6 上半场把 Agent 补成"会说人话、不花冤枉钱"的样子，下半场把它包装成"能演示、能复现"的样子。

## 1. 补 composer 的自然语言结论生成（2 小时，今天的核心）

### 1.1 现状与目标

现在 `node_compose`（`nodes/terminal_nodes.py`）是**规则拼装**：把结果前 10 行拼成文本，不调 LLM。目标改成：**用一次 LLM 调用，把（问题 + SQL + 结果集）总结成一句带结论的自然语言**——这一步才是"数据分析 Agent"和"SQL 翻译器"的分水岭。

### 1.2 新 composer（补丁式改法）

在 `terminal_nodes.py` 里新增一个带 LLM 的 compose 分支（保留原规则拼装作为 fallback）：

```python
# nodes/terminal_nodes.py 顶部追加
from src.datapilot.llm.client import LLMClient

COMPOSE_SYSTEM = "你是数据分析师，把 SQL 查询结果总结成一句严谨的中文结论。"

COMPOSE_USER = """# 用户问题
{question}

# 执行的 SQL
{sql}

# 查询结果的列名（顺序与数据行一一对应）
{columns}

# 查询结果（共 {n_rows} 行，最多展示前 {n_sample} 行，每行数据按上列列名顺序排列）
{sample}

要求：
1. 结论必须严格基于结果集，不推断、不补数据、不编单位或趋势。
2. 结论要直接回答用户问题：点名关键实体（如国家名、客户名、类别名）和关键数值，不要只说"共 N 行"这类元信息。
3. 结果被截断（truncated）时，明确说"前 N 行"而不是"全部"。
4. 结果为空时，直接说"未查询到符合条件的数据"，不臆测原因。
5. 只输出一句话结论，不超过 80 字。
只输出纯文本，不要 JSON。"""

> ⚠️ **踩坑（必须遵守，否则结论是废的）**：`{columns}` 占位符**不能省**。如果只把结果行当裸元组喂给模型（`str(tuple(r))`），模型看不到列名，只能瞎猜哪一列是金额/国家，会产出"消费额介于 37.62 至 42.62"这种空洞结论（既没点名实体、又可能是错的）。正确做法是 `sample` 拼成 `表头 + 数据行`，并把 `columns` 单独传进 format。
```

然后改 `node_compose`，让它**接收 client** 并生成结论（graph.py 里 compose 目前不传 client，需要改接线）：

```python
# nodes/terminal_nodes.py —— 把 node_compose 改成带 LLM 结论的版本
def node_compose(state: AgentState, client: LLMClient | None = None) -> dict:
    """产出 answer_text：默认走 LLM 生成一句结论；client 缺失时回退规则拼装。"""
    g = state.get("gate") or {}
    if state.get("behavior") == "clarify":
        return {"answer_text": f"需要澄清：{g.get('clarifying_question') or '请补充口径'}"}
    if state.get("behavior") == "refuse":
        return {"answer_text": f"无法回答：{g.get('reason') or '问题超出本数据库范围'}"}

    rows = state.get("rows")
    if not rows:
        return {"answer_text": "未查询到符合条件的数据。"}

    if client is None:
        # 回退：规则拼装（成本纪律，保证无 client 场景也能跑）
        header = " | ".join(str(c) for c in (state.get("columns") or []))
        body = "\n".join(" | ".join(str(v) for v in row) for row in rows[:10])
        suffix = "（结果已截断）" if state.get("truncated") else ""
        return {"answer_text": f"查询结果（{len(rows)} 行）{suffix}：\n{header}\n{body}"}

    # 带表头拼 sample：模型必须知道每列含义，否则只能瞎猜（会产出"消费额介于X至Y"这类空洞结论）
    cols = state.get("columns") or []
    header = " | ".join(str(c) for c in cols)
    body = "\n".join(" | ".join(str(v) for v in row) for row in rows[:10])
    sample = f"{header}\n{body}" if cols else str(tuple(rows[0])) if rows else "（空）"
    r = client.chat_json(COMPOSE_SYSTEM, COMPOSE_USER.format(
        question=state["question"], sql=state["sql"],
        columns=", ".join(str(c) for c in cols) or "（未知）",
        n_rows=len(rows), n_sample=min(10, len(rows)),
        sample=sample or "（空）"
    ), json_mode=False
    )
    # 结论调用也要记账（llm_calls/cost_cny 挂 operator.add Reducer）
    return {
        "answer_text": r.text.strip(),
        "llm_calls": 1, "cost_cny": r.cost_cny, "in_tokens": r.in_tokens,
    }
```

### 1.3 接线改动（graph.py 两处）

`build_graph` 里 compose 节点现在要传 client（和 generate/diagnose/repair 一样）：

```python
# graph.py —— 原：
#   g.add_node("compose", node_compose)
# 改为：
g.add_node("compose", lambda s: node_compose(s, _get_client(cache_path)))
```

同时 `pipelines/a3.py` / `a4.py` 的返回 dict 里**把 `answer_text` 带出来**（现在漏了）：

```python
# a3.py / a4.py 的 return dict 追加一行：
"answer_text": final.get("answer_text"),
```

### 1.4 让 runner 持久化 answer_text

`eval/runner.py` 的 `score_one` 现在只记 `sql`/`row_count` 等，没记 `answer_text`。在 `out` 处理后补一行：

```python
# runner.py score_one 里，rows = out.get("rows") 附近补：
answer_text = out.get("answer_text")
# ……最终返回的 record dict 里加：
"answer_text": answer_text,
```

### 1.5 让 review_sheet 抽得到结论文本

`scripts/make_review_sheet.py` 的每条记录里，把 `SQL` 那一行下面补一句结论：

```python
# make_review_sheet.py 的 lines += [...] 里，在 "- SQL" 之后加：
f"- 结论：{r.get('answer_text') or '（无）'}",
```

这样 review_sheet 抽出的 30 条里，每条都有"问题 / SQL / 结论 / 结果行数"，人工才能判断"结论是否做了过度断言"。

### 1.6 验收

```bash
python -m src.datapilot.cli ask --question "每个国家客户总消费额前 5 名"
# 预期：不再只是吐 SQL + 结果表，而是输出一句自然语言结论
python scripts/make_review_sheet.py chinook_a3 sakila_a3 ecommerce_a3
# 预期：review_sheet 每条出现"结论："字段，且有可读的自然语言（不是结果 dump）
```

**验收标准（三条都要满足，否则判不通过）：**

1. **点名实体 + 数值**：结论必须出现具体实体名（国家名/客户名/类别名等）和关键数值（金额、数量），不能只说"共 N 行 / 展示前 10 行"这类元信息。反例：`"消费额介于 37.62 至 42.62"`（空洞，未点名实体）。
2. **不含并列歧义**：排名类题若出现并列，结论要么如实说明"存在并列、前 N 名实际多于 N 人"，要么 SQL 用 `ROW_NUMBER()` 取恰好 N 行避免并列。反例：`"巴西第2名均为37.62"`（把金额当名次，病句）。
3. **SQL 窗口函数正确**：题目"前 N 名"默认用 `ROW_NUMBER()`（恰 N 行），不得用 `RANK()`（并列跳号导致溢出）或 `DENSE_RANK()`（并列挤名次）。这是 `a0.SYSTEM` 里已加的硬规则，若这里出现 RANK 说明规则没生效，需回头查 prompt 是否被覆盖。

> 注意：composer 加 LLM 会改变 A3/A4 的成本（每题多 1 次小调用）。但这是**必要的成本**——"结论"才是数据分析 Agent 的交付物。若担心成本，可让 compose 复用 `model_small`（`route_small` 同一套逻辑），Day 6 收尾时在日报里写清"结论生成的增量成本"。

### 1.7 踩坑复盘：两个真实的坑（已修，写进日报）

验收 §1.6 时实际踩了两个坑，都值得沉淀：

**坑 1：漏传列名 → 结论空洞。** 第一版 `sample` 用裸元组 `str(tuple(r))` 拼装，没带 `columns`。模型面对 `('Argentina', 1, 'Leone Köhler', 37.62, 1)` 这种无表头数据，不知道哪列是金额，只能瞎猜，产出 `"消费额介于 37.62 至 42.62"` 这种既没点名实体、又是错误区间的结论。**修法**：`sample` 拼成 `表头 + 数据行`，并把 `columns` 传进 `COMPOSE_USER`。

**坑 2：RANK 并列 → SQL 错 + 结论病句。** 模型生成"每个国家前 5 名"时用了 `RANK()`（并列跳号），导致 Brazil 第 2 名有 4 人并列 37.62，"前 5 名"实际多于 5 人（总行数 48→53，Canada 8 人/USA 7 人溢出），结论还出现病句 `"巴西第2名均为37.62"`。**修法**：在 `a0.SYSTEM` 加"排名口径"硬规则（前 N 名默认 `ROW_NUMBER()` 恰 N 行、禁 RANK/DENSE_RANK、排名窗口带稳定 tie-breaker），一次覆盖 A0~A4 所有 generate 节点。

`a0.py` 的 `SYSTEM` 里新增这段（与"业务口径"并列）：

```python
排名口径（必须严格遵守）：
- 题目要求"前 N 名/TOP N"时，默认用 ROW_NUMBER() 取恰好 N 行（每人一个不重复名次）。
- 不要用 RANK()（并列会跳号、导致"前 N 名"实际多于 N 人）或 DENSE_RANK()（并列会挤掉后续名次）。
- 除非题目明确要求"并列都要保留"，才可改用 RANK()。
- 排名窗口必须带稳定的 tie-breaker（如 ORDER BY 值 DESC, 主键 ASC），避免并列行顺序不确定。
```

> 这两坑其实是同一个方法论问题：**把"语义约束"显式化进 prompt**。列名是 compose 的语义约束、窗口函数是 generate 的语义约束——不写清楚，模型就会在无约束的空间里瞎猜。Day 7 写"已知局限"时，把"排序题并列/tie-breaker 口径"作为一个反复出现的系统性短板单列。

## 2. verifier 降级：砍 LLM judge，只留确定性 guard（1 小时）

### 2.1 决策依据（来自 Day 5 数据）

三库 15 个 run：`verify_fixed` 全 0，`verify_false_alarm` 仅 ecommerce_a4 的 ec-042（1 例，且是模型语义误读、verify 判 pass 没拦）。错误自信样本 < 5，检验力不足。**按决策树：不保留 LLM judge，执行"降级"——只留 `deterministic_flags`（整列 NULL / 全 NULL / 截断），做成零成本 guard。**

### 2.2 改法

`nodes/verifier.py` 的 `node_verify` 里，**删掉 LLM 调用那段**，只保留确定性检查：

```python
def node_verify(state: AgentState, client: LLMClient) -> dict:
    """【Day 6 降级】只做确定性 guard，不再调 LLM judge。
    依据：Day 5 三库 verify_fixed=0、误杀 1 例（非 verify 责任），LLM judge 无正收益。
    保留 deterministic_flags 作为零成本拦截；client 参数保留签名以兼容接线，但不使用。"""
    flags = deterministic_flags(
        state.get("rows"), state.get("columns"), state.get("truncated"))
    verdict = "wrong" if flags else "pass"
    return {"verify": {"verdict": verdict, "reason": "确定性检查",
                       "flags": flags}}
```

> 保留 `client` 参数是为了不改 graph.py 的 `lambda s: node_verify(s, _get_client(cache_path))` 接线——降级后它成了 unused 参数，加一行 `del client` 或在 docstring 说明即可。若想彻底干净，可同步改 graph.py 去掉传参，但要记得 `_get_client` 仍被 diagnose/repair/generate 用，别误删。

### 2.3 效果与代价（写进日报）

- **省 token**：A3/A4 每题少 1 次 LLM verify 调用，单题成本应明显下降（Day 5 的 A3 单题 ¥0.0065 → 预期降到 ¥0.004 上下）。
- **代价**：`deterministic_flags` 只能拦"整列 NULL / 全 NULL / 截断"这类客观异常，拦不住"执行成功但答案语义错"。这是**有意的取舍**——Day 5 数据证明 LLM judge 在这个评测集上也拦不住那类错（0 收益），不如省下钱。

### 2.4 验收

重跑 A3/A4 全量（新 run_id），对比：
- `verify_fixed` 仍为 0（没退化）
- 单题成本明显下降
- EX 不变（确定性 guard 不改变结果）

## 3. 可观测：tracer + trace_viewer（1.5 小时）

> 对应总手册 Day 6 交付物。目标：一次运行的**每次 LLM 调用和节点流转**能落成 JSONL trace，且能可视化调用树。

### 3.1 tracer.py（新建 `src/datapilot/obs/tracer.py`）

```python
"""把一次评测/一次 ask 的完整调用链落成 JSONL trace。
每条 trace 记录：时间戳、节点名、输入摘要、输出摘要、token、耗时、错误。
"""
import json
import threading
import time
from pathlib import Path


class Tracer:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._f = self.path.open("a", encoding="utf-8")
        self._lock = threading.Lock()  # runner 多线程共享一个 trace 文件，写必须串行

    def log(self, event: str, **fields) -> None:
        rec = {"ts": time.time(), "event": event, **fields}
        line = json.dumps(rec, ensure_ascii=False, default=str) + "\n"
        with self._lock:
            self._f.write(line)
            self._f.flush()

    def close(self) -> None:
        with self._lock:
            self._f.close()
```

### 3.2 trace_viewer.py（新建 `src/datapilot/obs/trace_viewer.py`）

```python
"""把 trace JSONL 打印成缩进调用树。用法：python -m src.datapilot.obs.trace_viewer <trace.jsonl>"""
import json
import sys
from collections import defaultdict


def main(path: str) -> None:
    rows = [json.loads(l) for l in open(path, encoding="utf-8")]
    # 按 question_id 分组；llm_call 等事件若没带 question_id，归到最近一次 question 事件
    by_q = defaultdict(list)
    cur = None
    for r in rows:
        if r.get("event") == "question":
            cur = r.get("question_id", "?")
        by_q[cur or "?"].append(r)
    for qid, rs in by_q.items():
        print(f"== {qid} ==")
        for r in rs:
            ev = r.get("event", "?")
            tok = r.get("in_tokens", 0) + r.get("out_tokens", 0)
            hit = " [cache]" if r.get("cache_hit") else ""
            model = r.get("model", "")
            print(f"  {ev:<10} {model:<14} tokens={tok:<6} cost=¥{r.get('cost_cny', 0):.6f} "
                  f"ms={r.get('latency_ms', 0)}{hit}")
            if ev == "question":
                print(f"    └─ 问题：{r.get('question', '')[:60]}")


if __name__ == "__main__":
    main(sys.argv[1])
```

### 3.3 接入：让 chat_json 记 trace（核心改动，4 个文件）

**光有 Tracer 类不会自动生效**，必须把它接到 `LLMClient.chat_json` 上，否则跑任何东西都不产 trace。改 4 处：

**① `llm/client.py` — `LLMClient.__init__` 加 tracer 参数：**

```python
def __init__(self, s=settings, cache_path: str | None = None, tracer=None):
    self.s = s
    self._client = OpenAI(api_key=s.api_key, base_url=s.base_url)
    from src.datapilot.llm.cache import LLMCache
    self._cache = LLMCache(cache_path) if cache_path else None
    self._tracer = tracer  # Day 6 §3：可选的 Tracer，None 时零开销
```

**② `llm/client.py` — 缓存命中分支 + 正常返回分支各记一条：**

```python
# 缓存命中分支（token=0，不记 trace 会让人困惑"这次调用怎么没花 token"）：
if hit is not None:
    if self._tracer is not None:
        self._tracer.log("llm_call", model=kwargs["model"],
                         in_tokens=0, out_tokens=0, cost_cny=0.0,
                         latency_ms=round((time.perf_counter() - t0) * 1000),
                         cache_hit=True)
    return LLMResult(...)

# 正常返回前（拿到 result 之后）：
if self._tracer is not None:
    self._tracer.log("llm_call", model=result.model,
                     in_tokens=result.in_tokens, out_tokens=result.out_tokens,
                     cost_cny=result.cost_cny, latency_ms=result.latency_ms,
                     cache_hit=False)
```

**③ `graph.py` — `_get_client` 和 `build_graph` 透传 tracer：**

```python
def _get_client(cache_path: str | None = None, tracer=None) -> LLMClient:
    key = (cache_path, id(tracer)) if tracer is not None else cache_path
    if key not in _clients:
        _clients[key] = LLMClient(cache_path=cache_path, tracer=tracer)
    return _clients[key]

def build_graph(checkpoint_db, with_reliability=False, cfg=None, tracer=None):
    ...
    # 6 个 LLM 节点的 _get_client(cache_path) 全部改成 _get_client(cache_path, tracer)
    # generate / diagnose / repair / compose / gate / verify
```

**④ `cli.py` — `ask` 命令加 `--trace` 参数：**

```python
@app.command("ask")
def cmd_ask(question: str = "", db: str = "chinook",
            thread: str = "cli-default", resume: str = "", trace: str = ""):
    from src.datapilot.obs.tracer import Tracer
    tracer = Tracer(trace) if trace else None
    if tracer is not None:
        tracer.log("question", question_id=f"ask-{thread}", question=question, db=db)
    app = build_graph("checkpoints-cli.db", with_reliability=True, tracer=tracer)
    ...
    if tracer is not None:
        tracer.close()
```

> ⚠️ **踩坑（checkpoint 污染）**：实测发现 `llm_calls` 和 trace 条数对不上（15 vs 3），根因是 `checkpoints-cli.db` 残留历史 checkpoint——反复用同一 `thread_id="cli-default"` 时 langgraph 会恢复旧执行历史、把 llm_calls 累加。**教训：ask 演示/评测务必用唯一 thread_id（或换新 checkpoint 文件），否则结果被静默污染。** 换全新 thread_id 后 llm_calls 与 trace 条数严格一致。

### 3.4 验收

跑一次 `ask` 或 `eval --limit 1`，产出 trace 文件，`trace_viewer` 能打出调用树，且 token/成本/延迟对得上 meta.json。

```bash
python -m src.datapilot.cli ask --question "每个国家客户总消费额前 5 名" --trace experiments/trace/demo.jsonl
python -m src.datapilot.obs.trace_viewer experiments/trace/demo.jsonl
# 预期：question 事件 + 若干条 llm_call（generate/verify/compose），各带 model/token/cost/ms
```

## 4. Demo + 工程化（2 小时，可砍的部分）

### 4.1 Streamlit 单页（`app.py`，< 100 行）

输入框 → 调 `graph_answer_a3`（或 a4）→ 展示 answer_text + SQL + 结果表 + 耗时/成本。**用 `st.session_state` 存一个线程，避免每次 rerun 重构图。**

```python
import streamlit as st
from src.datapilot.pipelines.a3 import graph_answer_a3
from src.datapilot.eval.eval_config import load_eval_config

st.title("DataPilot — 数据分析 Agent")
q = st.text_input("问点什么：", "每个国家客户总消费额前 5 名")
if st.button("执行") and q:
    cfg = load_eval_config("a3")
    out = graph_answer_a3({"question": q, "db_id": "chinook",
                           "difficulty": 3, "id": "demo"}, cfg=cfg)
    st.markdown(f"**结论**：{out.get('answer_text')}")
    st.code(out.get("sql"), language="sql")
    st.write(f"耗时 {out.get('extra', {}).get('latency_ms', 0)}ms · "
             f"成本 ¥{out.get('cost_cny', 0):.5f}")
```

> 依赖：`uv add streamlit`。**不加也能交付**（README 里写清楚 Demo 是 CLI 的 `ask` 命令），Streamlit 是加分项不是底线。

### 4.2 Dockerfile（一键起）

```dockerfile
FROM python:3.13-slim
WORKDIR /app
COPY pyproject.toml ./
COPY src ./src
COPY data ./data
COPY eval ./eval
RUN pip install -e .
EXPOSE 8501
CMD ["streamlit", "run", "app.py"]
```

> 验收：换一台机器 `docker build && docker run -p 8501:8501` 能起，`ask` 命令能跑。**若时间不够，Docker 可砍，但 README 的"快速开始"必须能在一台干净机器上复现。**

## 5. 收尾验收清单

- [ ] composer 产出自然语言结论，`ask` 命令输出不再是纯结果 dump
- [ ] `answer_text` 从 pipeline → runner → results.jsonl → review_sheet 全链路打通
- [ ] `make_review_sheet.py` 重跑后，30 条每条有"结论"字段，人工可勾"错误自信率"
- [ ] verifier 降级后重跑 A3/A4，`verify_fixed` 仍 0、成本下降、EX 不变
- [ ] tracer + trace_viewer 能打印一次运行的调用树
- [ ] Streamlit 单页能起（或明确写"Demo 走 CLI ask"）
- [ ] README 快速开始可复现（换机器能跑）
- [ ] 日报：结论生成的增量成本 + verifier 降级的成本收益 + 错误自信率数字（这次真的有数字了）

## 6. 砍单顺序（时间不够时）

1. 砍 Dockerfile（README 写清楚本地跑法即可）
2. 砍 Streamlit（Demo 用 CLI ask 代替）
3. 砍节点级 trace（只留 LLM 级 trace）
4. **不许砍**：composer 自然语言结论（这是"错误自信率"能落地的唯一前提）、verifier 降级（这是 Day 5 悬而未决的债）

## 7. 今天的关键判断（面试要能讲）

- **为什么补"结论生成"：** 数据分析 Agent 的交付物是"结论"不是"SQL"。没有自然语言结论，"错误自信率"这个指标根本不存在——而这恰恰是比 EX 更锋利的卖点（EX 只能测"答案对不对"，错误自信率测"对答案的叙述可不可信"）。
- **为什么降级 verifier：** 诚实负结果比硬撑正收益更有说服力。Day 5 三库证明 LLM judge 零收益，砍掉它省下的是真金白银的 token，同时保留确定性 guard 兜底客观异常。面试被问"verifier 有用吗"，答"在这个评测集上没测出收益，所以降级了"——这是工程成熟度的体现。
