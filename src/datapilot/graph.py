# A2 的图。checkpointer 的 thread_id 用 f"{run_id}:{question_id}"——
# 跨 run 复用同一 checkpoints.db 时旧 state 会污染新 run。
import sqlite3  # 【改】新版 SqliteSaver.from_conn_string 返回上下文管理器，需手动建连接

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import StateGraph, START, END

# settings / _client / _retrievers 各产生两份实例）
from src.datapilot.llm.client import LLMClient
from src.datapilot.nodes.common_nodes import node_retrieve, node_generate, node_validate, node_execute
from src.datapilot.nodes.diagnoser import node_diagnose
from src.datapilot.nodes.repairer import node_repair
from src.datapilot.nodes.terminal_nodes import node_compose, node_give_up
from src.datapilot.state import AgentState

# A3
from src.datapilot.nodes.gate import node_gate, node_clarify_wait
from src.datapilot.nodes.verifier import node_verify

_clients: dict = {}  # cache_path -> LLMClient；None 键即原单例语义


# 改为按缓存路径分键（A2/A3 调用方式不变）
def _get_client(cache_path: str | None = None, tracer=None) -> LLMClient:
    key = (cache_path, id(tracer)) if tracer is not None else cache_path
    if key not in _clients:
        _clients[key] = LLMClient(cache_path=cache_path, tracer=tracer)
    return _clients[key]


def build_graph(checkpoint_db: str, with_reliability: bool = False, cfg: dict | None = None,
                tracer=None):
    cfg = cfg or {}
    cache_path = cfg.get("cache_path")      # 仅 A4 传
    # 函数内所有 _get_client() 调用改为 _get_client(cache_path, tracer)

    g = StateGraph(AgentState)
    g.add_node("retrieve", node_retrieve)
    g.add_node("generate", lambda s: node_generate(s, _get_client(cache_path, tracer)))
    g.add_node("validate", node_validate)
    g.add_node("execute", node_execute)
    g.add_node("diagnose", lambda s: node_diagnose(s, _get_client(cache_path, tracer)))
    g.add_node("repair", lambda s: node_repair(s, _get_client(cache_path, tracer)))
    g.add_node("give_up", node_give_up)
    g.add_node("compose", lambda s: node_compose(s, _get_client(cache_path, tracer)))

    if with_reliability:
        # —— A3：gate + verify 接入 ——
        g.add_node("gate", lambda s: node_gate(s, _get_client(cache_path, tracer)))
        g.add_node("clarify_wait", node_clarify_wait)
        g.add_node("verify", lambda s: node_verify(s, _get_client(cache_path, tracer)))

        g.add_edge(START, "retrieve")
        g.add_edge("retrieve", "gate")
        g.add_conditional_edges("gate", _route_after_gate,
            {"generate": "generate", "clarify_wait": "clarify_wait", "compose": "compose"})
        g.add_edge("clarify_wait", "retrieve")  # 用户澄清后带新问题重走检索
    else:
        # —— A2 原拓扑，不动 ——
        g.add_edge(START, "retrieve")
        g.add_edge("retrieve", "generate")

    # —— A2 原拓扑，不动 ——
    g.add_conditional_edges("generate",
        lambda s: "validate" if s.get("sql") else "diagnose",
        {"validate": "validate", "diagnose": "diagnose"})
    g.add_conditional_edges("validate",
        lambda s: "execute" if not s.get("error") else "diagnose",
        {"execute": "execute", "diagnose": "diagnose"})

    if with_reliability:
        g.add_conditional_edges("execute", _route_after_execute_reliability,
            {"verify": "verify", "diagnose": "diagnose"})
        g.add_conditional_edges("verify", _route_after_verify,
            {"compose": "compose", "diagnose": "diagnose"})
    else:
        # 【改】execute 的条件边必须放进 else——原来 if 块内外各注册了一次，
        # 同一源节点重复注册 Branch 会在 compile 时抛 ValueError，A2 也跑不了
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


def _route_after_gate(s: AgentState) -> str:
    action = (s.get("gate") or {}).get("action", "answer")
    if action == "clarify":
        return "clarify_wait" if s.get("hitl") else "compose"
    if action == "refuse":
        return "compose"
    return "generate"


def _route_after_execute_reliability(s: AgentState) -> str:
    if s["exec_ok"] and s.get("rows"):
        return "verify"   # 成功且有行 → 校验
    return "diagnose"     # 报错或空结果 → 诊断（A2 原路径）


def _route_after_verify(s: AgentState) -> str:
    verdict = (s.get("verify") or {}).get("verdict", "pass")
    if verdict == "wrong" and not s.get("verify_retried"):
        return "diagnose"  # 打回修复，仅限一次
    return "compose"       # pass；或已打回过一次 → 认栽接受现状，防震荡


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
