# 这是一个 Markdown 评测报告生成器。核心职责是：把 run_eval 产出的 records（逐题记录）和 summary（聚合指标）连同 meta.json（运行上下文），渲染成一份人类可读的 report.md。
# 一句话：它是评测流水线的"最后一公里"——把冷冰冰的 JSONL 变成可以直接贴进周报、PR、复盘文档的报表。


from __future__ import annotations

import json
from pathlib import Path

from datapilot.eval.metrics import type_breakdown


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
        f"| EX（无序） | {summary['ex']:.2%} |",
        f"| EX（有序） | {summary['ex_ordered']:.2%} |",
        f"| SQL/执行错误率 | {summary['error_rate']:.2%} |",
        f"| 特殊题行为正确率 | {summary['behavior_ok']:.2%} |",
        f"| 延迟 P50 / P95 | {summary['latency_p50_ms']} / {summary['latency_p95_ms']} ms |",
        f"| 单题成本 | ¥{summary['cost_per_q_cny']:.6f} |",
        f"| 总成本 | ¥{summary['total_cost_cny']:.4f} |",
        f"| 平均 LLM 调用次数 | {summary['avg_llm_calls']} |",
        "",
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
