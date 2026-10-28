# give_up 与 compose（Day 4 版：产出 answer_text）

from src.datapilot.state import AgentState


def node_give_up(state: AgentState) -> dict:
    d = state.get("diagnosis") or {}
    reason = d.get("reason") or "unknown"
    out = {"give_up_reason": reason, "rows": None, "answer_text": f"无法回答：{reason}"}
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