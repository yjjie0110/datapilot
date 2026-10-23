# 这是项目的 命令行入口（CLI）。用 typer 把前面所有模块串成三条可执行命令：
# 命令	        |   对应流水线环节
# verify-gold	|   数据集自检（verify_gold.py）
# eval	        |   跑评测 + 出报告（runner.py + report.py）
# ask	        |   单题即席提问（a0.py）
# 一句话：它是把"一堆 Python 模块"变成"一个人能用的工具"的那层壳——开发者不用写代码，敲命令就能校验数据、跑基准、单题调试。


from __future__ import annotations

import shutil
from pathlib import Path

import typer
from rich import print as rprint

from datapilot.config import settings, PROJECT_ROOT
from datapilot.eval.report import write_report
from datapilot.eval.runner import run_eval
from datapilot.eval.verify_gold import verify_gold

app = typer.Typer(add_completion=False, no_args_is_help=True)


@app.command("verify-gold")
def cmd_verify_gold(dataset: str = ""):
    r = verify_gold(dataset or settings.dataset, settings.db_dir, settings.max_rows)
    rprint(f"总题数：{r['total']}")
    for p in r["problems"]:
        rprint(f"[yellow]{p}[/yellow]")
    rprint("[green]完成，请逐条目检 gold_result[/green]")


@app.command("eval")
def cmd_eval(
    config: str = "a0",
    limit: int = 0,
    concurrency: int = 0,
    run_id: str = "",
    dataset: str = "",
):
    out = run_eval(
        config_name=config,
        dataset_path=dataset or None,
        limit=limit or None,
        concurrency=concurrency or None,
        run_id=run_id or None,
    )
    rprint(out["summary"])
    src = write_report(out["run_dir"], out["records"], out["summary"], config)
    dst = Path(PROJECT_ROOT / "reports") / f"{out['run_id']}.md"
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(src, dst)
    rprint(f"[green]报告：{dst}[/green]")


@app.command("ask")
def cmd_ask(question: str, db: str = "chinook"):
    from datapilot.pipelines.a0 import a0_answer
    out = a0_answer({"id": "adhoc", "db_id": db, "question": question,
                     "expected_behavior": "answer"})
    rprint(f"SQL: {out.get('sql')}")
    rows = out.get("rows")
    rprint(f"行数: {0 if rows is None else len(rows)}")
    rprint((rows or [])[:5] if rows is not None else out.get("error"))


if __name__ == "__main__":
    app()
