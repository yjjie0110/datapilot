# 这是一个 Text-to-SQL 场景下的 SQL 安全执行器。
# 核心职责是：把 LLM 生成的 SQL 经过校验后，安全、只读、限时限量地在 SQLite 上执行，并返回结构化结果。
# 它同时兼顾了「防破坏」「防慢查询」「防超大结果」三重保护。

from __future__ import annotations

import time
from pathlib import Path

import sqlglot
from sqlglot import exp

from datapilot.tools.schema import connect_ro


# 从 sqlglot.exp 里按名字取类，取不到或不是类就跳过（安全地拿可选节点类型）
def _classes(names: list[str]) -> tuple:
    out = []
    for n in names:
        t = getattr(exp, n, None)  # getattr(x, 'y') is equivalent to x.y
        if isinstance(t, type):
            out.append(t)
    return tuple(out)

# 允许的「查询类」语句——SELECT 以及集合运算 UNION / INTERSECT / EXCEPT
SELECTISH = _classes(["Select", "Union", "Intersect", "Except"])
# 任何位置出现这些节点就拒绝——增删改、DDL、PRAGMA、ATTACH、事务控制等
BANNED = _classes([
    "Insert", "Update", "Delete", "Drop", "Create", "Alter",
    "Command", "Pragma", "Attach", "Detach", "Transaction",
])


# 把 SQLite 报错归类
def classify_error(msg: str) -> str:
    m = msg.lower()
    if "no such table" in m:
        return "NO_SUCH_TABLE"
    if "no such column" in m:
        return "NO_SUCH_COLUMN"
    if "syntax error" in m:
        return "SYNTAX_ERROR"
    if "interrupted" in m:
        return "TIMEOUT"
    if "misuse" in m:
        return "MISUSE"
    if "ambiguous" in m:
        return "AMBIGUOUS_COLUMN"
    return "OTHER"


# AST 白名单守卫。「不要用正则」——正则容易被注释、字符串字面量、大小写、换行等绕过；AST 白名单是更可靠的方式
def is_safe_select(sql: str) -> tuple[bool, str]:
    """基于 AST 的白名单，不要用正则做这件事。"""
    if not sql or not sql.strip():  # 空串直接拒
        return False, "empty_sql"
    try:  # 解析为 AST，解析失败也算拒绝
        stmts = [s for s in sqlglot.parse(sql, read="sqlite") if s is not None]
    except Exception as e:  # 语法错误也一并拦下
        return False, f"parse_error: {e}"
    # 必须只有 1 条语句——防 SELECT 1; DROP TABLE x; 这种注入
    if len(stmts) != 1:
        return False, f"expected_1_statement_got_{len(stmts)}"
    # 顶层语句必须属于 SELECTISH——不是就直接拒
    stmt = stmts[0]
    if not isinstance(stmt, SELECTISH):
        return False, f"not_select: {type(stmt).__name__}"
    # 递归查找有没有 BANNED 节点——即使是 SELECT，里面嵌了 INSERT ... RETURNING、ATTACH、PRAGMA 也拒
    for cls in BANNED:
        if stmt.find(cls) is not None:
            return False, f"banned_node: {cls.__name__}"
    return True, ""


# 强制限流，防止limit 999999 等大量输出的情况
# 注意一个已知弱点：这层包裹不能阻止 LLM 里那个 LIMIT 本身过大（如 LIMIT 999999），只是保证「没写 LIMIT 时也不会拉爆」。真正防止一次拉回太多是靠这个外层 + truncated 标记
def enforce_limit(sql: str, max_rows: int) -> str:
    """没有 LIMIT 就包一层子查询强制限流，防止一次拉回整库。"""
    stmts = [s for s in sqlglot.parse(sql, read="sqlite") if s is not None]
    # 如果原 SQL 已经有 LIMIT，原样返回
    if stmts and stmts[0].args.get("limit"):
        return sql
    # 否则外层包一层子查询加 LIMIT {max_rows}
    # 直接字符串拼 LIMIT 到原 SQL 尾部，遇到 ... ORDER BY x 或 ... UNION ... 会出错；
    # 包成 SELECT * FROM (...) AS _dp_sub LIMIT N 通用得多；
    # 先去尾部 ; 以免子查询里出现分号
    return f"SELECT * FROM ({sql.rstrip().rstrip(';')}) AS _dp_sub LIMIT {max_rows}"


# 主执行函数（核心）
def run_sql(
    db_path: str | Path,
    sql: str,
    *,
    max_rows: int = 200,
    timeout_s: float = 10.0,
) -> dict:
    t0 = time.perf_counter()
    # 1.先过守卫 is_safe_select
    ok, reason = is_safe_select(sql)
    # 不通过就直接返回 error_code="GUARD"，根本不碰数据库
    if not ok:
        return {
            "ok": False, "error": f"guard: {reason}", "error_code": "GUARD",
            "columns": [], "rows": [], "truncated": False, "elapsed_ms": 0,
        }

    # 2.enforce_limit 包一层限流
    wrapped = enforce_limit(sql, max_rows)
    conn = None

    try:
        # 3.只读连接 connect_ro(db_path)
        conn = connect_ro(db_path)
        # 4.设置超时——SQLite 的 set_progress_handler
        deadline = time.monotonic() + timeout_s
        # sqlite 的进度回调：返回非 0 即中断查询，抛 OperationalError: interrupted
        # SQLite 每执行约 2 万条 VM 指令就回调一次；
        # 这是 SQLite 里唯一可靠的超时机制（busy_timeout 只管锁等待，不管长查询）；
        conn.set_progress_handler(
            lambda: 1 if time.monotonic() > deadline else 0, 20_000
        )
        # 5.执行并取结果
        cur = conn.execute(wrapped)
        cols = [d[0] for d in cur.description]  # cur.description 给出列名
        rows = [list(r) for r in cur.fetchall()]  # Row 对象转成普通 list，方便 JSON 序列化
        return {
            "ok": True, "error": None, "error_code": None,
            "columns": cols, "rows": rows,
            "truncated": len(rows) >= max_rows,  # 是否可能被截断
            "elapsed_ms": round((time.perf_counter() - t0) * 1000),  # 耗时（毫秒）
        }
    # 任何异常都走 classify_error 归类，仍返回统一结构，永不向上抛——方便上层批量跑评测；
    except Exception as e:
        msg = str(e)
        return {
            "ok": False, "error": msg, "error_code": classify_error(msg),
            "columns": [], "rows": [], "truncated": False,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000),
        }
    finally:  # 确保连接关闭
        if conn is not None:
            conn.close()


# 采样辅助
# 复用 run_sql 取某表的头几行；
# 典型用途：把「表名 + 前 3 行」一起塞进 prompt，让 LLM 对数据形态有直觉；
# 失败静默返回空列表，符合"采样失败不该中断主流程"的场景。
def sample_rows(db_path: str | Path, table: str, n: int = 3) -> list[list]:
    r = run_sql(db_path, f'SELECT * FROM "{table}"', max_rows=n)
    return r["rows"] if r["ok"] else []