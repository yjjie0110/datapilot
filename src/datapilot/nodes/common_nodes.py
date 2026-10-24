# 四个主流程节点。generate 的首次生成复用 a0.SYSTEM——公平性红线。

from datapilot.config import settings
from datapilot.llm.client import LLMClient
from datapilot.nodes.schema_retriever import SchemaRetriever
from datapilot.pipelines.a0 import SYSTEM, extract_json
from datapilot.state import AgentState
from datapilot.tools.schema import full_schema_text, schema_text_for
from datapilot.tools.sql_runner import is_safe_select, run_sql

_retrievers: dict[str, SchemaRetriever] = {}


def _retriever(db_id: str) -> SchemaRetriever:
    if db_id not in _retrievers:
        _retrievers[db_id] = SchemaRetriever(settings.db_dir / f"{db_id}.db")
    return _retrievers[db_id]


def node_retrieve(state: AgentState) -> dict:
    db = settings.db_dir / f"{state['db_id']}.db"
    if state.get("escalated"):
        # 检索扩大：一次性退回全量 schema
        tables = [u["table"] for u in _retriever(state["db_id"]).units]
        schema = full_schema_text(db)
    else:
        # 只获取和当前question 相关的前top_k 个tables
        tables = _retriever(state["db_id"]).retrieve(state["question"], top_k=state["top_k"])
        schema = schema_text_for(db, tables)
    return {"retrieved_tables": tables, "schema_text": schema}


def node_generate(state: AgentState, client: LLMClient) -> dict:
    user = f"# 数据库 Schema\n{state['schema_text']}\n\n# 用户问题\n{state['question']}"

    # 调用LLM return {text:..., model:..., in_token:..., out_token:..., cost_cny:..., latency_ms:...}
    # 其中 text{"sql": "...", "tables_used": ["表名"], "assumptions": ["你对题意做出的任何假设"]}
    r = client.chat_json(SYSTEM, user)
    out = {"llm_calls": 1, "cost_cny": r.cost_cny, "in_tokens": r.in_tokens}
    try:
        # 将模型LLM 输出的格式严格成JSON 格式
        payload = extract_json(r.text)
        out["sql"] = payload.get("sql", "")
        out["error"] = None
    except Exception as e:
        out["sql"] = None
        out["error"] = f"parse_error: {e}"
    return out


def node_validate(state: AgentState) -> dict:
    # AST 白名单守卫
    ok, reason = is_safe_select(state["sql"] or "")
    return {"exec_ok": False, "error": None if ok else f"unsafe_sql: {reason}"}


def node_execute(state: AgentState) -> dict:
    # 执行sql，用 sql_runner.run_sql：AST 守卫、强制 LIMIT、只读、超时、错误分类；
    # return {"ok":..., "error":..., "error_code":...,"columns":..., "rows":...,"truncated":..., "elapsed_ms":...,}
    res = run_sql(
        settings.db_dir / f"{state['db_id']}.db", state["sql"],
        max_rows=settings.max_rows, timeout_s=settings.sql_timeout_s,
    )
    out = {
        "exec_ok": res["ok"], "error": res["error"], "error_code": res["error_code"],
        "columns": res["columns"], "rows": res["rows"] if res["ok"] else None,
        "truncated": res["truncated"],
    }
    if res["ok"] and state.get("first_rows") is None and not state["sql_history"]:
        out["first_rows"] = res["rows"]  # 首轮成功执行的快照，给 ex_first 用
    return out
