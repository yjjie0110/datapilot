# 修复节点：带错误反馈与历史，避免重复同样的错误。
# 【改】统一 datapilot.* 导入（同 graph.py，避免模块双重加载）
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
    parts = []
    # 列表为空或只有 1 条也不会报错（返回 [] 或 1 条），比 [-2]、[-1] 安全
    for h in state["sql_history"][-2:]:
        # 有 error 就显示错误，否则显示行数
        detail = h.get("error") or f"{h.get('n_rows', 0)} 行"
        parts.append(f"- {h['sql']}  → {detail}")
    history = "\n".join(parts) or "（无）"

    d = state.get("diagnosis") or {}
    # 直接报错优先（执行期错误最具体）；否则用诊断器的结构化结论（分类 + 原因）
    feedback = state.get("error") or f"诊断：{d.get('category')} - {d.get('reason')}"

    # 调用LLM.chat_json return {text:..., model:..., in_token:..., out_token:..., cost_cny:..., latency_ms:...}
    # 其中 text: {"sql": "...", "tables_used": [...], "assumptions": [...]}
    r = client.chat_json(REPAIR_SYSTEM, REPAIR_USER.format(
        schema=state["schema_text"], question=state["question"],
        sql=state["sql"], feedback=feedback, history=history,
    ))
    out = {"llm_calls": 1, "cost_cny": r.cost_cny, "in_tokens": r.in_tokens}
    try:
        out["sql"] = extract_json(r.text).get("sql", "")
        out["error"] = None
        out["error_code"] = None  # 【改】清掉陈旧 error_code（同 common_nodes）
    except Exception as e:
        out["error"] = f"parse_error: {e}"
        out["error_code"] = None
    # return out{"llm_calls", "cost_cny", "in_tokens", "sql", "error"}
    return out
