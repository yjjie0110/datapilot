# A3 = A2 + gate + verifier + composer。与 a2.py 的差异处用 ★ 标出。

import threading
import time
import uuid

from src.datapilot.graph import build_graph


def graph_answer_a3(q: dict, client=None, cfg: dict | None = None) -> dict:
    cfg = cfg or {}
    t0 = time.perf_counter()
    # ★1 打开可靠性组件；checkpoint 仍按线程隔离（Day 3 的并发锁教训）
    app = build_graph(f"checkpoints-{threading.get_ident()}.db",
                      with_reliability=True)
    final = app.invoke(
        {
            "question": q["question"], "db_id": q["db_id"],
            "trace_id": f"a3-{q['id']}",
            "top_k": cfg.get("top_k", 6),
            "max_attempts": cfg.get("repair_max_attempts", 3),
            "difficulty": q.get("difficulty", 1),  # ★2 verifier 成本门控用
            "hitl": False,                          # ★2 评测链路不挂起
            "attempts": 0, "escalated": False, "sql_history": [],
            "verify_retried": False,
            "behavior": "answer", "cost_cny": 0.0, "in_tokens": 0, "llm_calls": 0,
        },
        # thread_id 带 uuid：防同题重跑时旧 checkpoint 状态泄漏（Day 3 教训）
        config={"configurable": {"thread_id": f"a3:{q['id']}:{uuid.uuid4().hex[:8]}"}},
    )
    # 【改】gate 拦截的行为（clarify/refuse）从未执行过 SQL，不该记成 sql_error——
    # 它会污染 error_rate：那是评测约定的"SQL/执行错误率"，行为误判应单列。
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
            "first_rows": final.get("first_rows"),  # runner 算完 ex_first 后会丢掉
            "diagnosis": final.get("diagnosis"),
            "error_code": final.get("error_code"),
            "gate": final.get("gate"),      # ★3 行为决策留痕（进 results.jsonl 可溯源）
            "verify": final.get("verify"),  # ★3 校验留痕
        },
        "answer_text": final.get("answer_text"),  # Day 6 追加
    }
