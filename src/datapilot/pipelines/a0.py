# 这是 Text-to-SQL 项目的 A0 baseline pipeline——最朴素、最"笨"的一条端到端单题流程：
# 取 schema → 拼 prompt → 一次 LLM 调用 → 解析 JSON → 执行 SQL → 返回统一结果。


from __future__ import annotations

import json
import re

from src.datapilot.config import settings
from src.datapilot.llm.client import LLMClient
from src.datapilot.tools.schema import full_schema_text
from src.datapilot.tools.sql_runner import run_sql

SYSTEM = """你是一名资深的 SQLite 数据分析师，任务是把用户的问题翻译成一条可执行的 SQLite 查询。

业务口径（必须严格遵守）：
- 商品的"在售"状态值是 status='on'（不是中文'在售'），"下架"是 status='off'。
- "成交订单"指 orders.status IN ('paid','shipped','completed')，cancelled/refunded 不算。
- "GMV/成交总金额"指成交订单的 payments.amount 求和（不是 order_items 的金额）。

排名口径（必须严格遵守）：
- 题目要求"前 N 名/TOP N"时，默认用 ROW_NUMBER() 取恰好 N 行（每人一个不重复名次）。
- 不要用 RANK()（并列会跳号、导致"前 N 名"实际多于 N 人）或 DENSE_RANK()（并列会挤掉后续名次）。
- 除非题目明确要求"并列都要保留"，才可改用 RANK()。
- 排名窗口必须带稳定的 tie-breaker（如 ORDER BY 值 DESC, 主键 ASC），避免并列行顺序不确定。


规则：
1. 只允许使用下面 schema 中出现的表和列，禁止臆造表名或列名。
2. 只生成一条查询语句，可以使用 CTE（WITH）。禁止任何写操作。
3. 不要输出 SQL 之外的任何解释文字。
4. 必须严格输出如下 JSON：
{"sql": "...", "tables_used": ["表名"], "assumptions": ["你对题意做出的任何假设"]}
"""

# 带缓存的 schema 读取
_schema_cache: dict[str, str] = {}

# 进程级缓存：同一 db_id 只读一次磁盘、算一次 schema。
# Chinook 这种小库影响不大，但换成大库（几百张表）时，PRAGMA table_info + count(*) 很贵，缓存是必要的；
def get_schema(db_id: str) -> str:
    if db_id not in _schema_cache:
        # 生成"表 + 行数 + 列 + 主键 + 外键"的文本
        _schema_cache[db_id] = full_schema_text(settings.db_dir / f"{db_id}.db")
    return _schema_cache[db_id]


# 容错 JSON 解析
def extract_json(text: str) -> dict:
    """三层容错，对应 LLM 输出的三种"不听话"""
    text = text.strip()  # 去掉首位空白（含换行、空格、\t）

    # 裹了 markdown 代码块：```json\n{...}\n```，先剥壳
    # 注意：只判断开头，不判断结尾。若开头是 ``` 但结尾缺失（LLM 输出被截断），后面两条 sub 也只会剥掉开头，留下不完整的 JSON，最终走到第 3 层
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)  # 剥开头
        text = re.sub(r"\n?```$", "", text)  # 剥结尾
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.S)  # 兜底——从垃圾文本里抠 JSON 对象
        if not m:
            raise
        return json.loads(m.group(0))


# 单题主流程（核心），能直接作为 pipeline_fn 传给 run_eval
def a0_answer(q: dict, client: LLMClient | None = None) -> dict:
    """A0：单次生成，无检索、无修复、无校验。故意做到最笨。"""
    client = client or LLMClient()
    schema = get_schema(q["db_id"])
    user = f"# 数据库 Schema\n{schema}\n\n# 用户问题\n{q['question']}"

    # 调模型
    # return {text:..., model:..., in_token:..., out_token:..., cost_cny:..., latency_ms:...}
    # 其中 text{"sql": "...", "tables_used": ["表名"], "assumptions": ["你对题意做出的任何假设"]}
    r = client.chat_json(SYSTEM, user)

    try:
        # 将模型LLM 输出的格式严格成JSON 格式，包括：
        #
        payload = extract_json(r.text)
    except Exception as e:
        # 解析失败 → status="parse_error"，不抛异常，返回结构化失败记录；
        # 注意这里仍然计入 cost_cny（钱已经花了），但 llm_calls=1——记账诚实
        return {
            "status": "parse_error", "sql": None, "rows": None,
            "error": f"parse_error: {e}", "behavior": "answer",
            "llm_calls": 1, "cost_cny": r.cost_cny,
        }

    sql = payload.get("sql", "")  # 获取JSON 中的sql 语句
    # 执行sql，用 sql_runner.run_sql：AST 守卫、强制 LIMIT、只读、超时、错误分类；
    # return {"ok":..., "error":..., "error_code":...,"columns":..., "rows":...,"truncated":..., "elapsed_ms":...,}
    res = run_sql(
        settings.db_dir / f"{q['db_id']}.db",
        sql,
        max_rows=settings.max_rows,
        timeout_s=settings.sql_timeout_s,
    )

    # 字段与 runner.score_one 的期望完全对齐（status / sql / rows / behavior / llm_calls / cost_cny / error），所以能直接作为 pipeline_fn 传给 run_eval
    return {
        "status": "ok" if res["ok"] else "sql_error",
        "sql": sql,
        "tables_used": payload.get("tables_used"),
        "assumptions": payload.get("assumptions"),
        "rows": res["rows"] if res["ok"] else None,
        "columns": res["columns"],
        "error": None if res["ok"] else res["error"],
        "error_code": res.get("error_code"),
        # A0 永远不澄清、不拒绝。这个"缺陷"就是我们后面要量化的差距。
        "behavior": "answer",
        "llm_calls": 1,
        "cost_cny": r.cost_cny,
    }

if __name__ == "__main__":
    pass