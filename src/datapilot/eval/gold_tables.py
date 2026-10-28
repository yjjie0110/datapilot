# 从 gold_sql 解析引用表名，回填到数据集的 gold_tables 字段。
# 关键细节：CTE 别名会被 sqlglot 当成 Table 节点，必须排除。

import json
from pathlib import Path

import sqlglot
from sqlglot import exp


def extract_tables(sql: str) -> list[str]:
    tree = sqlglot.parse_one(sql, read="sqlite")
    cte_aliases = {c.alias for c in tree.find_all(exp.CTE)}
    return sorted(
        {t.name for t in tree.find_all(exp.Table) if t.name not in cte_aliases}
    )


def backfill(dataset_path: str | Path) -> dict:
    ds = Path(dataset_path)
    items = [json.loads(l) for l in ds.read_text(encoding="utf-8").splitlines() if l.strip()]
    n = 0
    for it in items:
        if it.get("gold_sql"):
            it["gold_tables"] = extract_tables(it["gold_sql"])
            n += 1
    ds.write_text(
        "\n".join(json.dumps(x, ensure_ascii=False) for x in items),
        encoding="utf-8",
    )
    return {"backfilled": n, "total": len(items)}


if __name__ == "__main__":
    from src.datapilot.config import settings
    # print(backfill(settings.dataset))
    # print(backfill("D:\\download\\AI\\ChatGPT\\Work\\agent-project-1\\datapilot\data\\benchmarks\\sakila_v0.jsonl"))
