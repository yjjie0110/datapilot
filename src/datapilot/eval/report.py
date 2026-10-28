# 这是一个 Markdown 评测报告生成器。核心职责是：把 run_eval 产出的 records（逐题记录）和 summary（聚合指标）连同 meta.json（运行上下文），渲染成一份人类可读的 report.md。
# 一句话：它是评测流水线的"最后一公里"——把冷冰冰的 JSONL 变成可以直接贴进周报、PR、复盘文档的报表。


from __future__ import annotations

import json
from pathlib import Path

from src.datapilot.eval.metrics import type_breakdown


# a3 中的 行为混淆矩阵
def behavior_matrix(records: list[dict]) -> str:
    """行=期望行为，列=实际行为。"""
    from collections import Counter
    cnt = Counter((r["expected_behavior"], r.get("behavior") or "?") for r in records)
    behaviors = sorted({b for _, b in cnt})
    lines = ["| 期望 \\ 实际 | " + " | ".join(behaviors) + " |",
             "|" + " --- |" * (len(behaviors) + 1)]
    for exp in ("answer", "clarify", "refuse"):
        row = [str(cnt.get((exp, b), 0)) for b in behaviors]
        lines.append(f"| {exp} | " + " | ".join(row) + " |")
    return "\n".join(lines)


def write_report(run_dir: str | Path, records: list[dict], summary: dict, config: str) -> Path:
    run_dir = Path(run_dir)
    meta_path = run_dir / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}

    lines = [
        f"# 评测报告 — {config}",
        "",
        "## 环境",
        f"- 模型：`{meta.get('model')}`  temperature={meta.get('temperature')}",
        f"- Prompt 指纹：`{meta.get('prompt_fingerprint')}`",
        f"- 数据集：`{meta.get('dataset')}`，共 {summary['n_total']} 题（可判定 {summary['n_answerable']} 题）",
        f"- 开始时间：{meta.get('started_at')}",
        "",
        "## 汇总",
        "",
        "| 指标 | 值 |",
        "| --- | --- |",
        f"| EX（无序，分母=全部 {summary['n_answerable']} 道可判定题） | {summary['ex']:.2%} |",
        f"| 排序题 EX（有序，分母={summary['n_order_sensitive']} 道 order_sensitive 题） | {summary['ex_ordered']:.2%} |",
        f"| Schema 召回率 | {format(summary['schema_recall'], '.2%') if summary.get('schema_recall') is not None else 'N/A'} |",
        f"| 平均输入 token | {summary.get('avg_in_tokens') or 'N/A'} |",
        f"| SQL/执行错误率 | {summary['error_rate']:.2%} |",
        f"| 特殊题行为正确率 | {summary['behavior_ok']:.2%} |",
        f"| 延迟 P50 / P95 | {summary['latency_p50_ms']} / {summary['latency_p95_ms']} ms |",
        f"| 单题成本 | ¥{summary['cost_per_q_cny']:.6f} |",
        f"| 总成本 | ¥{summary['total_cost_cny']:.4f} |",
        f"| 平均 LLM 调用次数 | {summary['avg_llm_calls']} |",
        f"| 首轮正确率 | {format(summary['ex_first'], '.2%') if summary['ex_first'] is not None else 'N/A'} |",          # 【改】原样输出裸浮点，改百分比
        f"| 修复增益 | {format(summary['repair_gain'], '.2%') if summary['repair_gain'] is not None else 'N/A'} |",          # 【改】同上
        f"| 触发检索扩大次数 | {summary['n_escalated']} |",      # 【改】错字"出发"→"触发"；原行尾缺逗号，靠隐式拼接幸存
    ]
    # 【改】Day 4 的功过账：只有带 gate/verify 留痕的 run（A3+）才展示，A0-A2 报告保持干净
    if any(r.get("gate") for r in records):
        lines.append(f"| gate 误杀 answer 题数 | {summary['gate_false_kill']} |")
    if summary.get("n_verified"):
        lines += [
            f"| verify 触发数 | {summary['n_verified']} |",
            f"| verify 修复成功数 | {summary['verify_fixed']} |",
            f"| verify 误杀数 | {summary['verify_false_alarm']} |",
        ]
    lines += [
        "",
        "## 行为混淆矩阵",
        behavior_matrix(records),
        "## 分题型",
        "",
        "| 题型 | 题目数 | 可判定题 | EX |",
        "| --- | --- | --- | --- |",
    ]
    for t, n, n_ans, ex in type_breakdown(records):
        ex_txt = "-" if ex is None else f"{ex:.1%}"
        lines.append(f"| {t} | {n} | {n_ans} | {ex_txt} |")

    lines += ["", "## 失败清单（前 20 条）", ""]
    fails = [r for r in records if r.get("ex") is False]
    if not fails:
        lines.append("（无）")
    for r in fails[:20]:
        lines.append(f"- `{r['id']}` [{r['question_type']}] {r['question']}")
        lines.append(f"  - status={r['status']}  error={r.get('error')}")
        lines.append(f"  - 生成 SQL：`{(r.get('sql') or '')[:200]}`")
        if r.get("mismatch"):
            lines.append(f"  - 差异：{r['mismatch']}")

    lines += ["", "## 特殊题明细（澄清 / 拒绝）", ""]
    for r in records:
        if r["expected_behavior"] in ("clarify", "refuse"):
            lines.append(
                f"- `{r['id']}` 期望={r['expected_behavior']} 实际={r['behavior']} "
                f"ok={r['behavior_ok']}"
            )

    out = run_dir / "report.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    return out
