# verifier：拦截"非空错结果"——执行成功但答案不可信。
# 职责红线：只判不改。verdict=wrong 打回 diagnose，修 SQL 是 repairer 的事。

import json

from src.datapilot.llm.client import LLMClient
from src.datapilot.state import AgentState

VERIFY_SYSTEM = "你是苛刻的 SQL 结果评审。只输出严格 JSON。"

VERIFY_USER = """# 用户问题
{question}

# 生成的 SQL
{sql}

# 执行结果（共 {n_rows} 行，前 5 行）
{sample}

# 确定性检查告警
{flags}

逐项核对：① SELECT 的列是否回答了问题所问 ② WHERE/JOIN 与题面约束是否一致
③ 聚合粒度是否正确 ④ 结果行数/取值是否与题面预期矛盾。
拿不准就 pass——只拦截有明确证据的错误。
只输出 JSON：{{"verdict": "pass|wrong", "reason": "一句话"}}"""


def deterministic_flags(rows, columns, truncated) -> list[str]:
    """零成本的客观异常检测。纯函数、不依赖 state，方便单测。"""
    flags = []
    if truncated:
        flags.append("结果撞 max_rows 截断，可能不完整")
    if rows:
        if all(all(v is None for v in row) for row in rows):
            flags.append("所有行的所有列全为 NULL")
        elif columns:
            # 整列全 NULL：典型的 join 条件错误或列选错（Day 3 的 ch-021 就是这形态）
            null_cols = [c for i, c in enumerate(columns)
                         if all(row[i] is None for row in rows)]
            if null_cols:
                flags.append(f"整列全 NULL：{null_cols}")
    return flags


def node_verify(state: AgentState, client: LLMClient) -> dict:
    flags = deterministic_flags(
        state.get("rows"), state.get("columns"), state.get("truncated"))
    # 成本控制：无告警且低难度 → 免 LLM 直接 pass（不调 LLM 就不许返回累加字段）
    if not flags and (state.get("difficulty") or 1) < 3:
        return {"verify": {"verdict": "pass", "reason": "确定性检查通过，低难度免判",
                           "flags": []}}

    rows = state.get("rows") or []
    sample = "\n".join(str(tuple(r)) for r in rows[:5])
    # 调用 client.chat_json，返回 LLMResult：{text, model, in_tokens, out_tokens, cost_cny, latency_ms}
    # 其中 text = {"verdict": "pass|wrong", "reason": "一句话"}
    r = client.chat_json(VERIFY_SYSTEM, VERIFY_USER.format(
        question=state["question"], sql=state["sql"],
        n_rows=len(rows), sample=sample or "（空）",
        flags="；".join(flags) or "无"
    ))
    out = {"llm_calls": 1, "cost_cny": r.cost_cny, "in_tokens": r.in_tokens}
    try:
        v = json.loads(r.text)
        verdict = v.get("verdict", "pass")
        if verdict not in ("pass", "wrong"):
            verdict = "pass"  # fail-open，同 gate
    except Exception:
        verdict, v = "pass", {"reason": "verify 输出解析失败，默认放行"}
    out["verify"] = {"verdict": verdict, "reason": v.get("reason", ""), "flags": flags}
    return out
