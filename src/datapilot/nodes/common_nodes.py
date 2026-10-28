# 四个主流程节点。generate 的首次生成复用 a0.SYSTEM——公平性红线。

from src.datapilot.config import settings
from src.datapilot.llm.client import LLMClient
from src.datapilot.nodes.schema_retriever import SchemaRetriever
from src.datapilot.pipelines.a0 import SYSTEM, extract_json
from src.datapilot.state import AgentState
from src.datapilot.tools.schema import full_schema_text, schema_text_for
from src.datapilot.tools.sql_runner import is_safe_select, run_sql

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
    # 【改】generate/validate 直写 error 时必须同时清掉 error_code——
    # 否则上一轮 execute 留下的旧 error_code 会让 diagnoser 误判（陈旧值污染）
    out = {"llm_calls": 1, "cost_cny": r.cost_cny, "in_tokens": r.in_tokens}
    try:
        # 将模型LLM 输出的格式严格成JSON 格式
        payload = extract_json(r.text)
        out["sql"] = payload.get("sql", "")
        out["error"] = None
        out["error_code"] = None
    except Exception as e:
        out["sql"] = None
        out["error"] = f"parse_error: {e}"
        out["error_code"] = None
    return out


def node_validate(state: AgentState) -> dict:
    # AST 白名单守卫
    ok, reason = is_safe_select(state["sql"] or "")
    # 【改】同上：本节点产出的 error 无对应 error_code，显式清空
    return {"exec_ok": False, "error": None if ok else f"unsafe_sql: {reason}",
            "error_code": None}


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
    # 【改】追加 sql_history——之前全图没有任何节点写它，repairer 的"不要重复
    # 同样的错误"永远是空列表。TypedDict 无 reducer，手动拼接实现追加。
    entry = {
        "sql": state["sql"],
        "error": res["error"],
        "n_rows": len(res["rows"]) if res["ok"] else 0,
        "attempt": state.get("attempts", 0),
    }
    out["sql_history"] = (state.get("sql_history") or []) + [entry]
    if res["ok"] and state.get("first_rows") is None and not state["sql_history"]:
        out["first_rows"] = res["rows"]  # 首轮成功执行的快照，给 ex_first 用
    return out
