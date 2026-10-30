# give_up 与 compose（Day 4 版：产出 answer_text）

from src.datapilot.state import AgentState

# Day 6
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


def node_give_up(state: AgentState) -> dict:
    d = state.get("diagnosis") or {}
    reason = d.get("reason") or "unknown"
    out = {"give_up_reason": reason, "rows": None, "answer_text": f"无法回答：{reason}"}
    # 危险 SQL 被拦截 → 这是正确的拒答行为，不是失败
    if d.get("category") == "unsafe":
        out["behavior"] = "refuse"
    return out


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