# A2 的图。checkpointer 的 thread_id 用 f"{run_id}:{question_id}"——
# 跨 run 复用同一 checkpoints.db 时旧 state 会污染新 run。
import sqlite3  # 【改】新版 SqliteSaver.from_conn_string 返回上下文管理器，需手动建连接

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import StateGraph, START, END

# settings / _client / _retrievers 各产生两份实例）
from datapilot.llm.client import LLMClient
from datapilot.nodes.common_nodes import node_retrieve, node_generate, node_validate, node_execute
from datapilot.nodes.diagnoser import node_diagnose
from datapilot.nodes.repairer import node_repair
from datapilot.nodes.terminal_nodes import node_compose, node_give_up
from datapilot.state import AgentState

_client: LLMClient | None = None


def _get_client() -> LLMClient:
    global _client
    if _client is None:
        _client = LLMClient()
    return _client


def build_graph(checkpoint_db: str):
    g = StateGraph(AgentState)
    g.add_node("retrieve", node_retrieve)
    g.add_node("generate", lambda s: node_generate(s, _get_client()))
    g.add_node("validate", node_validate)
    g.add_node("execute", node_execute)
    g.add_node("diagnose", lambda s: node_diagnose(s, _get_client()))
    g.add_node("repair", lambda s: node_repair(s, _get_client()))
    g.add_node("give_up", node_give_up)
    g.add_node("compose", node_compose)

    g.add_edge(START, "retrieve")
    g.add_edge("retrieve", "generate")
    g.add_conditional_edges("generate",
        lambda s: "validate" if s.get("sql") else "diagnose",
        {"validate": "validate", "diagnose": "diagnose"})
    g.add_conditional_edges("validate",
        lambda s: "execute" if not s.get("error") else "diagnose",
        {"execute": "execute", "diagnose": "diagnose"})
    g.add_conditional_edges("execute", _route_after_execute,
        {"compose": "compose", "diagnose": "diagnose"})
    g.add_conditional_edges("diagnose", _route_after_diagnose,
        {"repair": "repair", "escalate": "retrieve", "accept": "compose", "give_up": "give_up"})
    g.add_edge("repair", "validate")
    g.add_edge("give_up", "compose")
    g.add_edge("compose", END)

    # 【改两处】
    # 将LangGraph 图的执行状态 检查点checkpointer 持久化存储到sqlite 数据库中
    # 1) 当前版本的 SqliteSaver.from_conn_string() 返回的是上下文管理器（contextlib._GeneratorContextManager），
    #    不是 saver 实例——不进入 with 就拿不到真正的 checkpointer。改为手动建连接直接构造。
    #    check_same_thread=False 是必须的：作用是解除 SQLite 默认的线程限制（LangGraph 可能在别的线程里执行节点。）
    # 2) compile 的 kwarg 是 checkpointer=，不是 checkpoint_db=。
    # 注意：在 SQLite 里，传入的字符串就是数据库文件的路径。sqlite3.connect() 会把它当作一个文件系统路径去打开（或自动创建）对应的数据库文件。
    conn = sqlite3.connect(checkpoint_db, check_same_thread=False)
    cp = SqliteSaver(conn)
    return g.compile(checkpointer=cp)


def _route_after_execute(s: AgentState) -> str:
    if s["exec_ok"] and s.get("rows"):
        return "compose"
    return "diagnose"  # 报错或空结果都进诊断


def _route_after_diagnose(s: AgentState) -> str:
    action = (s.get("diagnosis") or {}).get("action", "give_up")
    if action == "escalate":
        return "escalate"
    if action == "repair" and s["attempts"] < s["max_attempts"]:
        return "repair"
    if action == "accept":
        return "accept"
    return "give_up"


