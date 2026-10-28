import operator
from typing import Annotated, Any, Optional, TypedDict


class AgentState(TypedDict, total=False):
    # 输入
    question: str
    db_id: str
    trace_id: str
    top_k: int               # 初始 top_k（来自 eval config）
    max_attempts: int

    # 检索
    retrieved_tables: list[str]
    schema_text: str
    escalated: bool          # 是否已退回全量 schema（仅限 1 次）

    # 生成 / 修复
    sql: Optional[str]
    sql_history: list[dict]  # [{sql, error, n_rows, attempt}]
    attempts: int
    first_rows: Optional[list]  # 第一次成功执行的行（算首轮正确率用）

    # 执行
    exec_ok: bool
    error: Optional[str]
    columns: Optional[list]
    rows: Optional[list]
    truncated: bool

    # 诊断
    error_code: str | None
    diagnosis: Optional[dict]  # {category, action, reason}

    # 输出
    behavior: str            # answer / refuse
    give_up_reason: Optional[str]

    # 成本
    # 【改】三个累加字段必须挂 operator.add Reducer——TypedDict 默认是覆盖语义，
    # 不修的话 repair/escalate 链路上每个节点返回的 llm_calls=1 会互相覆盖，
    # 最终只剩最后一个节点的计数（实测：sa-015 实际 3+ 次调用，记录只有 1）
    cost_cny: Annotated[float, operator.add]
    in_tokens: Annotated[int, operator.add]
    llm_calls: Annotated[int, operator.add]

    # —— Day 4 新增 ——
    difficulty: int            # 题目难度，verifier 的 LLM judge 按它控制成本
    hitl: bool                 # True 时 clarify 走 interrupt 等人答（仅 CLI 演示链路）
    gate: Optional[dict]       # node_gate{action, reason, clarifying_question}
    verify: Optional[dict]     # node_verifier{verdict, reason, flags}
    verify_retried: bool       # verify 打回后已修复过一次（防 verify↔repair 震荡）
    answer_text: Optional[str] # compose 产出的人话结论
