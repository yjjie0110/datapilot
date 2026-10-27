# 这是 Text-to-SQL 评测流水线的 「打分 + 汇总」模块。核心职责分两块：
#   1. 判定标准答案与模型输出的结果集是否等价（归一化 + 多重集比较 + 差异说明）；
#   2. 把逐题记录聚合成评测指标（EX、错误率、行为正确率、延迟分位、成本、LLM 调用次数、按题型拆解）。
# 一句话：前面跑完模型拿到结果后，这里负责判对错、算分数、出报表。

from __future__ import annotations

from collections import Counter
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any, Sequence

NULL_SENTINEL = "<NULL>"


# 单元格归一化
def _norm_cell(v: Any, ndigits: int, casefold: bool) -> str:
    """
    :arg
        ndigits: 统一成定点小数的位数（默认2）
        casefold: 不区分大小写？（默认False，区分大小写）
    输入任意单元格，输出可比较的字符串。
    casefold 控制是否大小写折叠，默认由调用方传 False
    """
    if v is None:  # 让 NULL 有稳定可比较的表示，不会和 "None"/"null" 混淆
        return NULL_SENTINEL
    if isinstance(v, bool):  # 类型换成str（注意：必须放在int 之前判断，因为 Python 里bool 是int 子类，否则True 会变成"1.00"）
        return str(v)
    if isinstance(v, (Decimal, int, float)):
        # 统一成定点小数，容忍 COUNT(*) 返回 59(int) 和 AVG 返回 59.0(float) 的表示差异
        # return f"{round(float(v), ndigits):.{ndigits}f}"
        return f"{Decimal(str(v)).quantize(Decimal(10) ** -ndigits):.{ndigits}f}"

    if isinstance(v, (datetime, date, time)):  # 不同驱动返回的日期表示不一，统一成 ISO 格式
        return v.isoformat()
    if isinstance(v, bytes):  # BLOB 列统一成十六进制字符串
        return v.hex()
    s = str(v).strip()  # 去空白；casefold 比 lower 更彻底（德语 ß → ss 等）
    return s.casefold() if casefold else s

    # 关键设计点：
    #   数值统一成"定点小数"而不是 str(float)，是为了让 59、59.0、Decimal("59") 都变成 "59.00"——这是 Text-to-SQL 判分里最常踩的坑；
    #   casefold 默认 False，因为大多数数据集区分大小写；需要时（如对大小写不敏感的库）再开；
    #   NULL_SENTINEL 用特殊标记，避免和真实字符串 "NULL" 撞车。
    # _norm_row 对一行逐列归一化，normalize_rows 对多行批量处理。


# 把一行逐列归一化成 tuple，保证可哈希，供 Counter 使用
def _norm_row(row: Sequence[Any], ndigits: int, casefold: bool) -> tuple[str, ...]:
    return tuple(_norm_cell(c, ndigits, casefold) for c in row)


# 批量归一化，输入一般是Sequence[Sequence[Any]]；返回 list[tuple]
def normalize_rows(rows, *, ndigits: int = 2, casefold: bool = False):
    return [_norm_row(r, ndigits, casefold) for r in rows]


# 结果集等价判定（核心）
def results_equal(
    pred_rows: Sequence[Sequence[Any]],
    gold_rows: Sequence[Sequence[Any]],
    *,
    ordered: bool = False,
    ndigits: int = 2,
    casefold: bool = False,
) -> bool:
    """结果集等价判定。

    ordered=False: 多重集比较（行序无关，重复行计数）——主口径，符合 Text-to-SQL 大多数数据集（如 Spider、BIRD）的 EX 定义。
    ordered=True : 逐行严格比较——参考口径
    """
    if len(pred_rows) != len(gold_rows):  # 行数不同直接不等，快速失败
        return False
    p = normalize_rows(pred_rows, ndigits=ndigits, casefold=casefold)  # 每个元素进行归一化
    g = normalize_rows(gold_rows, ndigits=ndigits, casefold=casefold)
    if ordered:  # 默认False，跳过
        # list[tuple] 的逐元素比较，等价于逐行逐列严格相等，顺序敏感：[(1,2),(3,4)] != [(3,4),(1,2)]（除非先排序后再比）
        return p == g
    # 多重集比较：行序无关，重复行计数。Counter 要求元素可哈希，tuple[str,...] 满足。
    # c1 = Counter('abracadabra') ; c1 = Counter({'a': 5, 'b': 2, 'r': 2, 'c': 1, 'd': 1})
    return Counter(p) == Counter(g)


def explain_mismatch(pred_rows, gold_rows, *, ndigits=2, casefold=False) -> str:
    """人话版不一致原因，Day 5 写失败分析会大量用到。"""
    if len(pred_rows) != len(gold_rows):
        return f"row_count_diff pred={len(pred_rows)} gold={len(gold_rows)}"

    # 行数相同但第一行列数不同时报告列数差异
    if pred_rows and gold_rows and len(pred_rows[0]) != len(gold_rows[0]):
        return f"col_count_diff pred={len(pred_rows[0])} gold={len(gold_rows[0])}"

    # 行数、列数相同，里面元素有差异
    p = Counter(normalize_rows(pred_rows, ndigits=ndigits, casefold=casefold))
    g = Counter(normalize_rows(gold_rows, ndigits=ndigits, casefold=casefold))
    only_pred = list((p - g).elements())[:3]
    only_gold = list((g - p).elements())[:3]
    return f"row_diff only_pred={only_pred} only_gold={only_gold}"


# 汇总评测指标，输入已经runner.run_eval return后的结果
def aggregate(records: list[dict]) -> dict:
    """
    输入逐题记录列表，输出聚合指标字典
    每条记录预期字段：
        expected_behavior、ex、ex_ordered、status、latency_ms、cost_cny、llm_calls、behavior_ok、question_type
    """
    # 分成"可回答题"和"特殊行为题"两类
    answerable = [r for r in records if r.get("expected_behavior") == "answer"]
    special = [r for r in records if r.get("expected_behavior") in ("clarify", "refuse")]

    def rate(num: int, den: int) -> float:
        return round(num / den, 4) if den else 0.0

    ex = sum(1 for r in answerable if r.get("ex"))
    ord_records = [r for r in answerable if r.get("ex_ordered") is not None]
    ex_ord = sum(1 for r in ord_records if r.get("ex_ordered"))
    errs = sum(1 for r in answerable if r.get("status") != "ok")
    lat = sorted(r.get("latency_ms", 0) for r in records) or [0]

    ex_firsts = [r["ex_first"] for r in answerable if "ex_first" in r]

    return {
        "n_total": len(records),  # 总题数。
        "n_answerable": len(answerable),  # 可回答题数。
        "ex": rate(ex, len(answerable)),  # 可回答题的精确匹配率（主指标）。
        "ex_ordered": rate(ex_ord, len(ord_records)),  # 有序口径 EX，分母仍用 answerable
        # schema 召回率（A1 类 run 才有；None 表示该 run 无检索）
        "schema_recall": (
            lambda xs: round(sum(xs) / len(xs), 4) if xs else None
        )([r["schema_recall"] for r in answerable if r.get("schema_recall") is not None]),
        # 平均输入 token（成本的直接解释变量；A0 的 extra 里不放，向后兼容为 None）
        "avg_in_tokens": (
            lambda xs: round(sum(xs) / len(xs)) if xs else None
        )([r["in_tokens"] for r in records if r.get("in_tokens")]),
        "n_order_sensitive": len(ord_records),
        "error_rate": rate(errs, len(answerable)),  # 可回答题的错误率。
        "behavior_ok": rate(sum(1 for r in special if r.get("behavior_ok")), len(special)),  # 特殊行为题的正确率。
        "latency_p50_ms": round(lat[len(lat) // 2]),  # lat[len//2] 是"上中位数"（偶数长度取偏大的那个），但不是严格统计定义的中位数。对偶数长度，更常见的是取两个中间值的平均。
        "latency_p95_ms": round(lat[min(len(lat) - 1, int(len(lat) * 0.95))]),  # 这是"最近秩"的近似，不是严格分位数。
        "total_cost_cny": round(sum(r.get("cost_cny", 0.0) for r in records), 6),  # 总成本，6 位小数。
        "cost_per_q_cny": round(
            sum(r.get("cost_cny", 0.0) for r in records) / max(len(records), 1), 6
        ),  # 每题平均成本
        "avg_llm_calls": round(
            sum(r.get("llm_calls", 0) for r in records) / max(len(records), 1), 2
        ),  # 平均 LLM 调用次数，同样空输入问题。
        "ex_first": round(sum(ex_firsts) / len(ex_firsts), 4) if ex_firsts else None,  # 首轮正确率
        # 修复增益 = 最终 EX − 首轮正确率。本项目最想证明的数字。
        "repair_gain": (
            round(ex / len(answerable) - sum(ex_firsts) / len(ex_firsts), 4)
            if ex_firsts and answerable else None
        ),
        "n_escalated": sum(1 for r in records if r.get("escalated")),  # 触发检索扩大次数
    }


# 按题型拆 EX
def type_breakdown(records: list[dict]) -> list[tuple[str, int, int, float | None]]:
    """
    按题型拆 EX，用来诊断 headroom 到底卡在哪一类题上。
    返回 (question_type, n_total, n_answerable, ex_rate) 列表
    """
    groups: dict[str, list[dict]] = {}
    # 按 question_type 分组，缺失归为 "unknown"。
    for r in records:
        # dict.setdefault: 如果 key 不存在，就把它设成 default 并返回 default；如果已存在，就直接返回现有的值，不做任何修改。
        # d.setdefault(key, default=None)  等价于
        # if key not in d:
        #     d[key] = default
        # return d[key]
        groups.setdefault(r.get("question_type", "unknown"), []).append(r)

    rows = []
    # 按题型名排序，保证输出稳定
    for t, rs in sorted(groups.items()):
        # len(rs) 是该题型总题数，len(ans) 是可回答题数，ex_rate 分母用 ans
        ans = [r for r in rs if r.get("expected_behavior") == "answer"]
        ex = sum(1 for r in ans if r.get("ex"))
        rows.append((t, len(rs), len(ans), round(ex / len(ans), 3) if ans else None))
    return rows


# 失败二分函数——这是 A1 对比分析的核心
def failure_split(records: list[dict]) -> dict:
    """把 ex=False 的题分成两类：检索没召回 gold 表（retrieval）vs 召回了但生成错（generation）。
    只有带 retrieved_tables 的 run 才有意义。A0 的全错都该算 generation。"""
    retr = gen = 0
    for r in records:
        if r.get("ex") is not False or not r.get("gold_tables"):
            continue
        rt = r.get("retrieved_tables")
        if rt is None:
            gen += 1
        elif set(r["gold_tables"]) <= set(rt):
            gen += 1
        else:
            retr += 1
    return {"retrieval_errors": retr, "generation_errors": gen}
