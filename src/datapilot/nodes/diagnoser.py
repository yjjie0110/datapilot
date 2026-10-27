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


# 【改】签名改为 (err, error_code=None)：err 在前保持单参数兼容，
# 并补回文本兜底——generate/validate 节点直接写 error（无 error_code）时必须有文本路径
def classify_error(err: str, error_code: str | None = None) -> str:
    # 优先读 sql_runner 给的结构化 error_code（执行期错误走这里）
    code = (error_code or "").upper()
    if code in ("NO_SUCH_TABLE", "NO_SUCH_COLUMN"):
        return "schema_incomplete"
    if code == "SYNTAX_ERROR":
        return "syntax"
    if code == "GUARD":
        # sql_runner 内部守卫：解析失败是 "guard: parse_error: ..."，其余是危险 SQL
        return "parse" if "parse_error" in err.lower() else "unsafe"
    if code == "TIMEOUT":
        return "timeout"

    # 文本兜底（error_code 缺失：node_generate / node_validate 直写 error 的场景）
    e = err.lower()
    if "no such table" in e or "no such column" in e:
        return "schema_incomplete"
    if "parse_error" in e:
        return "parse"
    if "unsafe_sql" in e or "guard" in e:
        return "unsafe"
    if "syntax" in e:
        return "syntax"
    if "interrupted" in e or "timeout" in e:
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
        # 【改】把 execute 节点写入 state 的 error_code 传给分类器
        category = classify_error(err or "", state.get("error_code"))

    # 【改】diagnose 是所有失败路径的漏斗，在这里计入 attempts——
    # 否则 parse 失败（不进 execute）的死循环永远撞不到上限，只能靠递归限制崩溃兜底
    attempts = state["attempts"] + 1

    # 动作决策：unsafe 直接拒；schema 问题优先扩大检索（仅 1 次）；其余修复
    if category == "unsafe":
        action, reason = "give_up", "危险 SQL 被守卫拦截，正确行为是拒答"
    elif category in ("schema_incomplete", "empty_suspicious") and not state.get("escalated"):
        action, reason = "escalate", "schema 疑似不全，退回全量 schema 重新生成"
    else:
        action, reason = "repair", "带错误反馈修复"

    if attempts >= state["max_attempts"]:
        action, reason = "give_up", f"attempts 达到上限（{state['max_attempts']}）"

    # 【改】escalate 必须在这里就地置位——图中没有独立 escalate 节点，（graph中，将escalate 映射成retrieval）
    # 不置位的话 retrieve 永远走 top_k 分支，且 escalated 恒 False 会让
    # diagnose 反复选择 escalate，空转到 attempts 耗尽
    out = {
        "diagnosis": {"category": category, "action": action, "reason": reason},
        "attempts": attempts,
        "llm_calls": 1 if err is None and category != "unsafe" else 0,
    }
    if action == "escalate":
        out["escalated"] = True
    return out