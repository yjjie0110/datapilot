# 数据集「gold SQL」质量校验 + gold 结果缓存脚本

import json
from pathlib import Path

from datapilot.tools.sql_runner import run_sql


def verify_gold(dataset_path: str | Path, db_dir: str | Path, max_rows: int = 200) -> dict:
    """
    args:
        :param dataset_path: json文件路径
        :param db_dir: 数据库所在文件夹的路径
        :param max_rows: 输出的最大行数
    :return:
    """

    # 读取每行json，跳过空行
    ds = Path(dataset_path)
    raw = ds.read_text(encoding="utf-8").splitlines()
    # items 就是题目列表，每项通常有 id、db_id、question、gold_sql 等字段。
    items = [json.loads(l) for l in raw if l.strip()]

    problems: list[str] = []
    out: list[dict] = []

    for it in items:
        if not it.get("gold_sql"):
            out.append(it)  # clarify / refuse 题没有 gold
            continue
        db = Path(db_dir) / f"{it['db_id']}.db"
        res = run_sql(db, it["gold_sql"], max_rows=max_rows)
        if not res["ok"]:
            problems.append(f"[{it['id']}] gold SQL 执行失败: {res['error']}")
            out.append(it)
            continue
        rows = res["rows"]
        if len(rows) == 0:
            problems.append(f"[{it['id']}] gold 返回 0 行，几乎肯定写错了: {it['question']}")
        if len(rows) >= max_rows:
            problems.append(f"[{it['id']}] gold 返回 {len(rows)} 行，可能缺少聚合或过滤条件")
        it["gold_result"] = rows
        out.append(it)

    ds.write_text(
        "\n".join(json.dumps(x, ensure_ascii=False) for x in out),
        encoding="utf-8",
    )
    return {"total": len(items), "problems": problems}

if __name__ == "__main__":
    from datapilot.config import settings

    result = verify_gold(settings.dataset, settings.db_dir, settings.max_rows)
    print(result["total"])
    print(result["problems"])