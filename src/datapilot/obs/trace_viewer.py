"""把 trace JSONL 打印成缩进调用树。用法：python -m src.datapilot.obs.trace_viewer <trace.jsonl>"""
import json
import sys
from collections import defaultdict


def main(path: str) -> None:
    rows = [json.loads(l) for l in open(path, encoding="utf-8")]
    # 按 question_id 分组；llm_call 等事件若没带 question_id，归到最近一次 question 事件
    by_q = defaultdict(list)
    cur = None
    for r in rows:
        if r.get("event") == "question":
            cur = r.get("question_id", "?")
        by_q[cur or "?"].append(r)
    for qid, rs in by_q.items():
        print(f"== {qid} ==")
        for r in rs:
            ev = r.get("event", "?")
            tok = r.get("in_tokens", 0) + r.get("out_tokens", 0)
            hit = " [cache]" if r.get("cache_hit") else ""
            model = r.get("model", "")
            print(f"  {ev:<10} {model:<14} tokens={tok:<6} cost=¥{r.get('cost_cny', 0):.6f} "
                  f"ms={r.get('latency_ms', 0)}{hit}")
            if ev == "question":
                print(f"    └─ 问题：{r.get('question', '')[:60]}")


if __name__ == "__main__":
    main(sys.argv[1])
