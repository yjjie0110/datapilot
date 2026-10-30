# A4 = A3 + 缓存 + 路由。与 a3.py 的差异处用 ★ 标出。
import threading
import time
import uuid

from src.datapilot.graph import build_graph


def graph_answer_a4(q: dict, client=None, cfg: dict | None = None) -> dict:
    cfg = cfg or {}
    t0 = time.perf_counter()
    # ★1 缓存文件按 run 隔离不进这里——跨 run 共享才有开发循环收益，固定文件名
    a4_cfg = dict(cfg)
    if a4_cfg.get("cache"):
        a4_cfg["cache_path"] = "experiments/cache/llm_cache.db"
    app = build_graph(f"checkpoints-{threading.get_ident()}.db",
                      with_reliability=True, cfg=a4_cfg)  # ★2 cfg 进图
    final = app.invoke(
        {
            "question": q["question"], "db_id": q["db_id"],
            "trace_id": f"a4-{q['id']}",
            "top_k": cfg.get("top_k", 6),
            "max_attempts": cfg.get("repair_max_attempts", 3),
            "difficulty": q.get("difficulty", 1),
            "hitl": False,
            "route_small": bool(cfg.get("route_small")),   # ★3 路由开关进 state
            "attempts": 0, "escalated": False, "sql_history": [],
            "verify_retried": False,
            "behavior": "answer", "cost_cny": 0.0, "in_tokens": 0, "llm_calls": 0,
        },
        config={"configurable": {"thread_id": f"a4:{q['id']}:{uuid.uuid4().hex[:8]}"}},
    )
    # ★4 gate 拦截的行为（clarify/refuse）从未执行过 SQL，不能记成 sql_error——
    #    error_rate 的口径是"SQL/执行错误率"，行为误判会污染它（Day 4 a3.py 的实测教训）
    behavior = final.get("behavior", "answer")
    if behavior == "clarify":
        status = "clarified"
    elif behavior == "refuse":
        status = "refused"
    else:
        status = "ok" if final.get("exec_ok") else "sql_error"
    return {
        "status": status,
        "sql": final.get("sql"),
        "tables_used": final.get("retrieved_tables"),
        "assumptions": None,
        "rows": final.get("rows"),
        "columns": final.get("columns"),
        "error": final.get("error") or final.get("give_up_reason"),
        "behavior": final.get("behavior", "answer"),
        "llm_calls": final.get("llm_calls", 0),
        "cost_cny": final.get("cost_cny", 0.0),
        "retrieved_tables": final.get("retrieved_tables"),
        "extra": {
            "in_tokens": final.get("in_tokens"),
            "attempts": final.get("attempts"),
            "escalated": final.get("escalated"),
            "first_rows": final.get("first_rows"),
            "diagnosis": final.get("diagnosis"),
            "error_code": final.get("error_code"),
            "gate": final.get("gate"),
            "verify": final.get("verify"),
        },
        "answer_text": final.get("answer_text"),  # Day 6 追加
    }
