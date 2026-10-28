"""汇总 experiments/runs/ 下指定 run，生成 reports/ablation.md。
用法：python scripts/ablation_report.py
"""
import json
from pathlib import Path

RUNS = [  # (配置, 库, run_id)——与第 3 节的 run_id 一一对应，改了 run_id 这里同步改
    ("a0", "chinook", "a0_chinook_fix"), ("a0", "sakila", "a0_sakila_fix"),
    ("a1", "chinook", "a1_chinook_fix"), ("a1", "sakila", "a1_sakila_fix"),
    ("a2", "chinook", "a2_chinook_v3"), ("a2", "sakila", "a2_sakila_v3"),
    ("a3", "chinook", "a3_chinook_v2"), ("a3", "sakila", "a3_sakila_v2"),
    ("a4", "chinook", "a4_chinook"), ("a4", "sakila", "a4_sakila"),
] + [(c, "ecommerce", f"{c}_ecommerce") for c in ("a0", "a1", "a2", "a3", "a4")]

FIELDS = [("ex", "EX"), ("ex_first", "首轮EX"), ("repair_gain", "修复增益"),
          ("schema_recall", "召回率"), ("behavior_ok", "行为正确率"),
          ("gate_false_kill", "gate误杀"), ("verify_fixed", "verify修复"),
          ("verify_false_alarm", "verify误杀"), ("avg_in_tokens", "均token"),
          ("cost_per_q_cny", "单题成本"), ("latency_p95_ms", "P95ms")]


def main() -> None:
    import sys
    # 脚本从 scripts/ 启动时 sys.path[0]=scripts/，必须把项目根（含 src 包）加进去
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from src.datapilot.eval.metrics import aggregate

    rows = []
    for cfg_name, db, run_id in RUNS:
        p = Path("experiments/runs") / run_id / "results.jsonl"
        if not p.exists():
            rows.append((cfg_name, db, None))
            continue
        recs = [json.loads(l) for l in p.open(encoding="utf-8") if l.strip()]
        rows.append((cfg_name, db, aggregate(recs)))

    dbs = ["chinook", "sakila", "ecommerce"]
    lines = ["# 消融矩阵（自动生成，数据可溯源到 run_id）", ""]
    for db in dbs:
        lines.append(f"## {db}")
        lines.append("| 配置 | " + " | ".join(n for _, n in FIELDS) + " |")
        lines.append("| --- |" + " --- |" * len(FIELDS))
        for cfg_name, rdb, s in rows:
            if rdb != db:
                continue
            if s is None:
                lines.append(f"| {cfg_name} | " + " | ".join(["缺"] * len(FIELDS)) + " |")
                continue
            cells = []
            for k, _ in FIELDS:
                v = s.get(k)
                if v is None:
                    cells.append("—")
                elif k in ("ex", "ex_first", "repair_gain", "schema_recall",
                           "behavior_ok"):
                    cells.append(f"{v:.1%}")
                elif k == "cost_per_q_cny":
                    cells.append(f"¥{v:.4f}")
                else:
                    cells.append(str(v))
            lines.append(f"| {cfg_name} | " + " | ".join(cells) + " |")
        lines.append("")
    out = Path("reports/ablation.md")
    out.write_text("\n".join(lines), encoding="utf-8")
    print("报告：", out.resolve())


if __name__ == "__main__":
    main()
