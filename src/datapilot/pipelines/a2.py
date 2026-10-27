# A2 = A1(top_k 冻结) + 修复环。pipeline_fn 接口与 a0/a1 完全对齐——
# 这是 Day 1 接口设计的兑现时刻：runner 一行不改。

import json
import threading  # 【改】per-thread checkpoint 文件
import time
import uuid  # 【改】thread_id 需要唯一后缀

from datapilot.config import settings
from datapilot.graph import build_graph


def graph_answer(q: dict, client=None, cfg: dict | None = None) -> dict:
    cfg = cfg or {}
    t0 = time.perf_counter()
    trace_id = f"a2-{q['id']}"
    # 【改】checkpoint 文件按线程隔离：runner 用 4 线程并发跑题，所有线程共写
    # 同一个 checkpoints.db 会撞 SQLite 单写者限制（实测出现 database is locked /
    # attempt to write a readonly database，v2 两组 run 共 4 题因此报废）。
    # 每线程一个文件：同线程内题目串行无竞争，跨线程物理隔离。
    app = build_graph(f"checkpoints-{threading.get_ident()}.db")
    final = app.invoke(
        {
            "question": q["question"], "db_id": q["db_id"], "trace_id": trace_id,
            "top_k": cfg.get("top_k", 6),
            "max_attempts": cfg.get("repair_max_attempts", 3),
            "attempts": 0, "escalated": False, "sql_history": [],
            "behavior": "answer", "cost_cny": 0.0, "in_tokens": 0, "llm_calls": 0,
        },
        # 【改】thread_id 加 uuid：否则同 config+题号重跑会复用旧 checkpoint，
        # first_rows/escalated 等不在输入里的字段从上一轮泄漏进新一轮（状态污染）
        config={"configurable": {"thread_id": f"{cfg.get('name', 'a2')}:{q['id']}:{uuid.uuid4().hex[:8]}"}},
    )
    return {
        "status": "ok" if final.get("exec_ok") else "sql_error",
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
            "first_rows": final.get("first_rows"),   # runner 算完 ex_first 后会丢掉
            "diagnosis": final.get("diagnosis"),
            "error_code": final.get("error_code"),   # 【改】暴露给失败归因统计
        },
    }
