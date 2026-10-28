# A1 = A0 + schema 检索。其余一切（SYSTEM、模型、温度、JSON 格式）与 A0 完全一致。
# 公平性底线：A0 与 A1 的唯一差异是"喂给模型的 schema 文本从全量变成检索子集"。

from __future__ import annotations

from src.datapilot.config import settings
from src.datapilot.llm.client import LLMClient
from src.datapilot.nodes.schema_retriever import SchemaRetriever
from src.datapilot.pipelines.a0 import SYSTEM, extract_json  # 直接复用，禁止复制粘贴后改字
from src.datapilot.tools.schema import schema_text_for
from src.datapilot.tools.sql_runner import run_sql

_retrievers: dict[str, SchemaRetriever] = {}


def get_retriever(db_id: str) -> SchemaRetriever:
    if db_id not in _retrievers:
        # 将数据库.db 里的表存入bm25 中
        _retrievers[db_id] = SchemaRetriever(settings.db_dir / f"{db_id}.db")
    return _retrievers[db_id]


def a1_answer(q: dict, client: LLMClient | None = None, top_k: int = 6) -> dict:
    client = client or LLMClient()  # 获取llm
    retriever = get_retriever(q["db_id"])  # {"数据库名": SchemaRetriever 对象}
    # 从数据库中获取与question 的score 最高的top_k 条，tables = ["表名", ...]
    tables = retriever.retrieve(q["question"], top_k=top_k)
    schema = schema_text_for(settings.db_dir / f"{q['db_id']}.db", tables)
    user = f"# 数据库 Schema（检索子集）\n{schema}\n\n# 用户问题\n{q['question']}"

    # 调模型
    # return {text:..., model:..., in_token:..., out_token:..., cost_cny:..., latency_ms:...}
    # 其中 text{"sql": "...", "tables_used": ["表名"], "assumptions": ["你对题意做出的任何假设"]}
    r = client.chat_json(SYSTEM, user)
    try:
        payload = extract_json(r.text)  # 复用a0 中的容错 JSON 解析
    except Exception as e:
        return {
            "status": "parse_error", "sql": None, "rows": None,
            "error": f"parse_error: {e}", "behavior": "answer",
            "llm_calls": 1, "cost_cny": r.cost_cny,
            "retrieved_tables": tables,
            "extra": {"in_tokens": r.in_tokens, "schema_chars": len(schema)},
        }

    sql = payload.get("sql", "")  # 获取JSON 中的sql 语句

    # 执行sql （也就是llm 生成的sql），用 sql_runner.run_sql：AST 守卫、强制 LIMIT、只读、超时、错误分类；
    # return {"ok":..., "error":..., "error_code":...,"columns":..., "rows":...,"truncated":..., "elapsed_ms":...,}
    res = run_sql(
        settings.db_dir / f"{q['db_id']}.db", sql,
        max_rows=settings.max_rows, timeout_s=settings.sql_timeout_s,
    )
    return {
        "status": "ok" if res["ok"] else "sql_error",
        "sql": sql,
        "tables_used": payload.get("tables_used"),
        "assumptions": payload.get("assumptions"),
        "rows": res["rows"] if res["ok"] else None,
        "columns": res["columns"],
        "error": None if res["ok"] else res["error"],
        "error_code": res.get("error_code"),
        "behavior": "answer",
        "llm_calls": 1,
        "cost_cny": r.cost_cny,
        "retrieved_tables": tables,  # q 中相关的top_k 个表
        "extra": {"in_tokens": r.in_tokens, "schema_chars": len(schema)},
    }
