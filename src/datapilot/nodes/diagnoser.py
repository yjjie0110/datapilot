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


def classify_error(error_code: str | None, err: str) -> str:
    code = (error_code or "").upper()
    if code in ("NO_SUCH_TABLE", "NO_SUCH_COLUMN"):
        return "schema_incomplete"
    if code == "SYNTAX_ERROR":
        return "syntax"
    if code == "GUARD":
        return "parse" if "parse_error" in err.lower() else "unsafe"
    if code == "TIMEOUT":
        return "timeout"
    return "other"



def node_diagnose(state: AgentState, client: LLMClient) -> dict:
    err = state.get("error")

    # 空结果分支：LLM 判断可疑性
    if not err and state.get("exec_ok") and not state.get("rows"):
        # 调用LLM.chat_json return {text:..., model:..., in_token:..., out_token:..., cost_cny:..., latency_ms:...}
        # 其中 text: {"suspicious": true, "reason": "一句话"}
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
        if not suspicious:  # 若空结果，用LLM 判断不可疑
            return {"diagnosis": {"category": "empty_ok", "action": "accept", "reason": reason}}
        # 若空结果，LLM 判断可疑
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