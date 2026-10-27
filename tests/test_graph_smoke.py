from datapilot.eval.eval_config import load_eval_config
from datapilot.nodes.diagnoser import classify_error


def test_classify_error_deterministic():
    assert classify_error("no such table: Foo") == "schema_incomplete"
    assert classify_error("no such column: x") == "schema_incomplete"
    assert classify_error('near "SELET": syntax error') == "syntax"
    assert classify_error("unsafe_sql: 非 SELECT/WITH") == "unsafe"
    assert classify_error("parse_error: xxx") == "parse"


def test_unsafe_gives_refuse():
    # 危险 SQL → give_up → behavior=refuse，不需要 LLM
    from datapilot.nodes.terminal_nodes import node_give_up
    out = node_give_up({"diagnosis": {"category": "unsafe", "reason": "r"}, "rows": [1]})
    assert out["behavior"] == "refuse" and out["rows"] is None


def test_graph_smoke_real_llm():
    # 全图冒烟：1 道真题，断言接口字段齐全（需要 API Key，CI 可跳过）
    import json
    q = {"id": "ch-001", "db_id": "chinook",
         "question": "列出所有巴西客户的姓名和邮箱。"}
    from datapilot.pipelines.a2 import graph_answer
    out = graph_answer(q, cfg=load_eval_config("a2"))
    for k in ("status", "sql", "rows", "behavior", "retrieved_tables"):
        assert k in out
    assert out["status"] == "ok"
