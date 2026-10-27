# DataPilot Day 4 实施手册 —— 校验与行为决策（A3）

> 输入状态：A2 双库已跑通（v3），修复增益在 sakila 兑现（+5.56pt，sa-015）。
> 今天的目标：解决 Day 3 数据暴露的三类 A2 修不了的失败。
> 预计 6–7 小时。

## 0. 今天全部工作的出发点（15 分钟，先读懂）

Day 3 v3 的失败解剖，三条结论对应今天的三个新组件：

| Day 3 证据 | 失败模式 | 今天的对策 |
| --- | --- | --- |
| ch-021/022、sa-013/014：rows>0、diag=None、ex=False | **非空错结果**——执行成功但答错，diagnose 看不到 | verifier |
| behavior_ok=0，ch-027 被 escalate 白烧一轮 | **歧义题被硬答**——该反问的没反问 | gate（clarify） |
| ch-030 编造 USA 归一化、ch-008 交 `WHERE 1=0` | **对抗题被编造答案**——该拒答的没拒答 | gate（refuse） |

一句话：A2 的修复环回答"SQL 错了怎么办"，A3 要回答"**这题该不该答、答案可不可信**"。

### 公平性红线（同前两天）

- A3 = A2（top_k=6、修复环、escalate 全部冻结）+ gate + verifier + composer。**唯一自变量是新增的三个组件**。
- generate 的 SYSTEM prompt 逐字节不变。新组件的 prompt 是新的，写进各自的指纹（顺手把"prompt 指纹写死 a0.SYSTEM"这笔债还了，见 5.3）。
- 改完先跑冒烟再开全量。

## 1. gate：clarify / refuse 前置拦截 `nodes/gate.py`（1.5 小时）

### 1.1 位置与理由

```
START → retrieve → gate ──answer──→ generate → ...（A2 原链路不变）
                      ├─clarify─→ compose（behavior=clarify，附反问文本）
                      └─refuse──→ compose（behavior=refuse，附理由）
```

放在 retrieve 后、generate 前：

- **retrieve 后**：判断"问题可不可答"需要知道 schema 里有什么——裸看问题判断不了"数据库里没有删除时间戳列"这类对抗题。
- **generate 前**：省一次生成 token；歧义题本来就不该生成 SQL。

### 1.2 实现

一次 LLM 调用，输入问题 + 检索到的表列清单（比全量 schema 短，gate 不该贵）：

```python
# gate：行为决策前置。只判"该不该答"，不生成 SQL。

import json

from datapilot.llm.client import LLMClient
from datapilot.state import AgentState

GATE_SYSTEM = "你是数据库问答的行为裁判。只输出严格 JSON。"

GATE_USER = """# 数据库 Schema（检索到的相关表）
{schema}

# 用户问题
{question}

判断该问题的行为类别：
- "answer"：问题明确、且所需信息在 schema 中存在
- "clarify"：问题有歧义（关键概念未定义，如"最受欢迎""最多"缺少口径），
  必须反问才能给出唯一正确答案
- "refuse"：问题引用了 schema 中不存在的实体/列/业务概念，
  或要求的信息从根本上无法由该库回答

只输出 JSON：{{"action": "answer|clarify|refuse", "reason": "一句话",
"clarifying_question": "若 clarify，给出反问句"}}"""


def node_gate(state: AgentState, client: LLMClient) -> dict:
    r = client.chat_json(GATE_SYSTEM, GATE_USER.format(
        schema=state["schema_text"], question=state["question"]))
    out = {"llm_calls": 1, "cost_cny": r.cost_cny, "in_tokens": r.in_tokens}
    try:
        verdict = json.loads(r.text)
        action = verdict.get("action", "answer")
        if action not in ("answer", "clarify", "refuse"):
            action = "answer"  # 非法输出一律放行——gate 误杀比漏判代价大
    except Exception:
        action, verdict = "answer", {"reason": "gate 解析失败，默认放行"}
    out["gate"] = {"action": action, "reason": verdict.get("reason", ""),
                   "clarifying_question": verdict.get("clarifying_question")}
    if action != "answer":
        out["behavior"] = action
    return out
```

**默认放行原则**：gate 的任何异常/非法输出都按 answer 处理。gate 误杀一道 answer 题 = EX 直接掉 4–5pt；漏判一道 clarify 题只是维持现状。不对称的代价决定保守的默认。

### 1.3 单测（必须先写）

```python
def test_gate_fail_open():
    # LLM 输出非法 JSON → 默认 answer，behavior 不变
    # LLM 输出未知 action → 默认 answer
    ...
```

### 1.4 state.py 增量

```python
    # 行为决策（Day 4）
    gate: Optional[dict]       # {action, reason, clarifying_question}
    verify: Optional[dict]     # {verdict, reason}（见第 2 节）
```

## 2. verifier：非空错结果拦截 `nodes/verifier.py`（2 小时）

### 2.1 位置

```
execute ──成功且 rows 非空──→ verify ──pass──→ compose
                                  └─suspicious/wrong──→ diagnose（category="wrong_result"）
```

### 2.2 两层设计：确定性检查 + LLM judge

**为什么不用总手册原案的"第二路径独立生成 + 结果比对"**：Day 3 的失败全是**系统性错误**（词形、中英映射、语义误读），不是随机抖动——双路径大概率犯同样的错，比对不出来，还白付 2× 生成成本。双路径适合抓"随机幻觉"，不适合抓"一致性误解"。这是对总手册的刻意偏离，日报里写明理由。

**第一层（确定性，零成本）**：

```python
def deterministic_flags(state: AgentState) -> list[str]:
    flags = []
    rows, cols = state.get("rows"), state.get("columns") or []
    if state.get("truncated"):
        flags.append("结果撞 max_rows 截断，可能不完整")
    if rows and all(all(v is None for v in row) for row in rows):
        flags.append("所有行的所有列全为 NULL")
    if rows and cols:
        # 整列全 NULL：典型的 join 条件错误或列选错
        null_cols = [c for i, c in enumerate(cols)
                     if all(row[i] is None for row in rows)]
        if null_cols:
            flags.append(f"整列全 NULL：{null_cols}")
    return flags
```

**第二层（LLM judge，只在第一层有 flags 或题目 difficulty>=3 时调用——控制成本）**：

```python
VERIFY_USER = """# 问题
{question}

# 生成的 SQL
{sql}

# 执行结果（前 5 行，共 {n} 行）
{sample}

# 确定性检查告警
{flags}

逐项核对：① SELECT 的列是否回答了问题所问 ② WHERE/JOIN 条件与题面约束是否一致
③ 聚合粒度是否正确 ④ 结果行数/取值是否与题面预期矛盾。
只输出 JSON：{{"verdict": "pass|wrong", "reason": "一句话"}}"""
```

**verdict=wrong → diagnose（category="wrong_result"）走 repair**。verifier **只打回不修 SQL**——单一职责，修复是 repairer 的事。

### 2.3 防抖动纪律（重要）

- 每题 verify 触发的 repair **最多 1 次**（state 加 `verify_retried: bool`），否则 verify↔repair 可能互相震荡到 attempts 耗尽。
- verifier 有自己的误杀率：把本来正确的结果判 wrong → repair 改错。**这个方向必须可测量**：
  extra 里记 `verify` 字段，收尾时用脚本统计 `ex_first=True 且 ex=False` 的题（被 verify 改错的），这就是误杀数。

### 2.4 单测

- 全 NULL 行 / 整列 NULL / 截断 → flags 非空
- 正常结果 → flags 空
- verdict=wrong → state 写 verify、行为正确（mock client）

## 3. composer 升级 `nodes/terminal_nodes.py`（30 分钟）

Day 3 的 compose 是空的。升级为：**结论只能引用执行结果**，输出文本答案（给用户看的一面），同时保留 rows 给 runner 判分。

```python
def node_compose(state: AgentState, client: LLMClient) -> dict:
    # gate 拦截的题不调用 LLM，直接用 gate 给的文本
    g = state.get("gate") or {}
    if state.get("behavior") == "clarify":
        return {"answer_text": g.get("clarifying_question") or "需要澄清"}
    if state.get("behavior") == "refuse":
        return {"answer_text": f"无法回答：{g.get('reason', '')}"}
    # answer：LLM 基于 rows 写结论，prompt 里禁止引用 rows 以外的数字
    ...
```

a2.py 的输出 dict 里加 `"answer_text": final.get("answer_text")`。runner 不用改（多出的字段被忽略），报告也不用改。

## 4. HITL 演示：interrupt() 接入 `ask` CLI（1 小时）

总手册验收要求"现场演示：提问 → Agent 反问 → 你回答 → 继续执行"。评测链路里 clarify 是直接停的（没有真人），HITL 是**演示链路**，两者共存：

- `cli.py` 的 `ask` 增加 `--thread` 参数：固定 checkpoint 文件（如 `checkpoints-cli.db`，**不要**用 per-thread 那套）+ 固定 thread_id。
- gate 判定 clarify 时 `interrupt()`（查你装的 langgraph 版本的 interrupt API，1.x 与 0.x 写法不同）。
- 用户回答后 `ask --resume` 用 Command(resume=...) 继续，把回答拼进 question 重走 generate。
- **这个演示不进评测**——eval 里 gate 仍然直接 compose。写在 README 的 demo 章节，面试现场用。

## 5. runner/指纹/指标收尾（45 分钟）

### 5.1 新指标（metrics.aggregate + report）

| 指标 | 计算 | 回答的问题 |
| --- | --- | --- |
| gate 误判数 | `expected_behavior=answer 且 behavior≠answer` 的题数 | gate 误杀（EX 直接损失） |
| verify 触发率 | extra 含 verify 的 answer 题占比 | verifier 活跃度 |
| verify 修正数 | ex_first=False 且 ex=True 且 verify.verdict=wrong | verifier 的功 |
| verify 误杀数 | ex_first=True 且 ex=False | verifier 的过 |

### 5.2 行为混淆矩阵

report 里加一张小表：行=expected_behavior（answer/clarify/refuse），列=实际 behavior。一眼看出 gate 在哪类题上犯晕。behavior_ok 一个数不够看了。

### 5.3 还指纹债

`prompt_fingerprint()` 目前写死 a0.SYSTEM。改为汇总所有 prompt 文本：a0.SYSTEM + REPAIR_SYSTEM + EMPTY_JUDGE + GATE_SYSTEM + VERIFY 的 system。拼起来算一个哈希。注意：**改完指纹全变，旧 run_id 全部不可续跑**——正好，A3 本来就要新开 run_id。

## 6. 实验与验收（1.5 小时）

```bash
# 冒烟：3 道题（1 answer + 1 clarify + 1 adversarial）先看行为对不看 EX
python -m src.datapilot.cli eval --config a3 --limit 5 --run-id a3_smoke

# 全量
python -m src.datapilot.cli eval --config a3 --run-id a3_chinook
python -m src.datapilot.cli eval --config a3 --dataset data/benchmarks/sakila_v0.jsonl --run-id a3_sakila
```

`eval/configs/a3.yaml`：

```yaml
pipeline: a3
top_k: 6
repair_max_attempts: 3
```

### 解读规则（数字出来对号入座）

- **behavior_ok 从 0 涨上来** → gate 起效。同时盯 gate 误判数：>1 道 answer 题被误判 → 先调 GATE_USER 再认数字。
- **sakila EX 在 A2 的 88.89% 基础上再涨** → verifier 拦截了非空错结果。看 verify 修正数归因。
- **EX 反而下降** → 查 verify 误杀数。误杀 ≥2 → verifier 太激进，LLM judge 收紧（只在确定性 flags 非空时启用）。
- **chinook EX 跌破 91.67%** → 大概率 gate/verify 误伤，逐题看，不许认账。

### 验收清单

- [ ] gate 单测（含 fail-open）+ verifier 单测全绿，全量 pytest 绿
- [ ] behavior 混淆矩阵：chinook 6 道特殊题至少 4 道行为正确
- [ ] sa-013/014 中至少 1 道被 verifier 拦截并修复（或有明确记录的拦截理由）
- [ ] verify 误杀数 ≤ 1
- [ ] HITL 演示可现场跑通（interrupt → resume）
- [ ] 三组数字（A1/A2/A3 × 双库）可同表对比，全部可溯源 run_id
- [ ] 日报含：对比表、混淆矩阵、verify 功过账、成本变化

## 7. 常见坑（今天专属）

1. **gate 放在 generate 后** → 白烧生成 token，且"该不该答"的决策被 SQL 草稿污染。
2. **verifier 直接改 SQL** → 职责混乱，归因时说不清是 verify 的功还是 repair 的功。
3. **LLM judge 对所有题启用** → 成本翻倍。用 difficulty/确定性 flags 做前置过滤。
4. **verify↔repair 无次数上限** → 震荡到死。verify_retried 只许一次。
5. **HITL 用 per-thread checkpoint 文件** → resume 时换了线程/进程，找不到 checkpoint。
6. **gate 误判不统计** → EX 掉了都不知道是生成变差还是 gate 误杀。
