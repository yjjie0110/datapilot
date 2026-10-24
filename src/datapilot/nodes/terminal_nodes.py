# give_up 与 compose

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
