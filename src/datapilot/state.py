from typing import Any, Optional, TypedDict


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
    cost_cny: float
    in_tokens: int
    llm_calls: int
