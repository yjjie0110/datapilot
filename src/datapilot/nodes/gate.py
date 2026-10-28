# gate：行为决策前置。只判"该不该答"，不生成 SQL。
# 设计纪律：fail-open——任何异常都按 answer 放行，误杀比漏判代价大。

import json

from src.datapilot.config import settings
from src.datapilot.llm.client import LLMClient
from src.datapilot.state import AgentState
from src.datapilot.tools.schema import table_units

GATE_SYSTEM = "你是数据库问答的行为裁判。只输出严格 JSON。"

GATE_USER = """# 全库表清单（该数据库拥有的全部表及列，判 refuse 的唯一依据）
{catalog}

# 检索到的相关表 Schema（供判断 answer/clarify 参考，可能不全）
{schema}

# 用户问题
{question}

判断该问题的行为类别：
- "answer"：问题明确、且所需信息在全库表清单中存在
- "clarify"：问题有歧义（关键概念未定义口径，如"最受欢迎""最活跃"），必须反问才能给出唯一正确答案
- "refuse"：满足任一条件才判 refuse——
  ① 问题引用的实体/列/业务概念在【全库表清单】中也不存在，
     或要求的信息从根本上无法由该库回答；
  ② 【写操作拒绝】问题要求修改/删除/插入数据（如"删掉""改成""清空""add 一条"），
     无论后半句是否带合法查询——本系统是只读分析 Agent，写操作整体拒绝
     （可在 reason 里说明：合法部分可以不改数据地回答）。
  注意：检索到的相关表不全不构成 refuse 理由——实体在全库清单里存在但检索结果
  中没有时，应判 answer（后续流程会自动扩大检索）。

只输出 JSON：{{"action": "answer|clarify|refuse", "reason": "一句话",
"clarifying_question": "若 clarify 给出反问句，否则为空字符串"}}"""

_VALID_ACTIONS = ("answer", "clarify", "refuse")


def _full_catalog(db_id: str) -> str:
    """全库表名紧凑清单：每张表一行 'TableName(col1, col2, ...)'。

    【方案 A】refuse 决策需要完备性知识——"检索到的部分 schema 里没有"不等于
    "全库没有"。检索漏表（如中文"歌单"召不回 Playlist）曾在 demo 中被 gate
    放大成误拒。该清单约 200 token，换来 refuse 决策的完备依据。
    清单加载失败遵循 gate 的 fail-open 纪律：降级为空清单而不是让 gate 崩溃。
    """
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
    # 调用 client.chat_json(system, user)，返回 LLMResult：{text, model, in_tokens, out_tokens, cost_cny, latency_ms}
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
