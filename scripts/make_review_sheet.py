"""从指定 run 抽 30 条"答对且给了结论"的记录，生成人工评审表。
用法：python scripts/make_review_sheet.py <run_id> [<run_id>...]
产出：reports/review_sheet.md——人工逐条勾选，勾完统计错误自信率。
"""
import json
import random
import sys
from pathlib import Path


def main(run_ids: list[str]) -> None:
    ROOT = Path(__file__).resolve().parent.parent

    pool = []
    for rid in run_ids:
        p = ROOT / "experiments/runs" / rid / "results.jsonl"
        for l in p.open(encoding="utf-8"):
            r = json.loads(l)
            # 只抽"答对"的：错答案的结论是另一个指标（失败归因）的事
            if r.get("ex") is True and r.get("behavior") in (None, "answer"):
                r["_run"] = rid
                pool.append(r)
    random.Random(42).shuffle(pool)          # 固定种子：抽样可复现
    sample = pool[:30]
    lines = ["# 错误自信率人工评审表", "",
             "口径：结论文本做出结果集不支持的断言即计一次（相关当因果 / "
             "样本当全体 / 忽略 NULL 或截断 / 编造单位与趋势）。", ""]
    for i, r in enumerate(sample, 1):
        lines += [
            f"## {i}. `{r['id']}`（{r['_run']}）",
            f"- 问题：{r['question']}",
            f"- SQL：`{(r.get('sql') or '')[:200]}`",
            f"- 结果行数：{r.get('row_count')}",
            "- [ ] 结论有过度断言（勾选即计一次错误自信）",
            "- 备注：", ""]
    (ROOT / "reports/review_sheet.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"已抽样 {len(sample)} 条 → reports/review_sheet.md")


if __name__ == "__main__":
    main(sys.argv[1:] or ["chinook_a3", "sakila_a3", "ecommerce_a3"])
