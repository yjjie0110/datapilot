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

from src.datapilot.config import settings, PROJECT_ROOT
from src.datapilot.eval.report import write_report
from src.datapilot.eval.runner import run_eval
from src.datapilot.eval.verify_gold import verify_gold

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
def cmd_ask(question: str = "", db: str = "chinook",
            thread: str = "cli-default", resume: str = "",
            trace: str = ""):
    """单题即席提问，支持 HITL 澄清：
    ask "哪个歌单最受欢迎？" --thread demo1
    ask --thread demo1 --resume "按购买次数"
    --trace 可选：把本次运行的 LLM 调用链落成 JSONL（Day 6 §3 可观测）
    """
    from langgraph.types import Command
    from src.datapilot.graph import build_graph
    from src.datapilot.obs.tracer import Tracer

    # Day 6 §3：可选 tracer（--trace 传路径则开启）
    tracer = Tracer(trace) if trace else None
    if tracer is not None:
        tracer.log("question", question_id=f"ask-{thread}", question=question, db=db)

    # ★ 固定 checkpoint 文件：评测那套 per-thread 文件（checkpoints-{线程id}.db）
    # 跨进程 resume 时找不到旧 checkpoint——演示链路必须用固定文件名
    app = build_graph("checkpoints-cli.db", with_reliability=True, tracer=tracer)
    cfg = {"configurable": {"thread_id": thread}}
    if resume:
        # langgraph 1.x：Command(resume=...) 把用户回答送回挂起的 interrupt 处
        final = app.invoke(Command(resume=resume), config=cfg)
    else:
        final = app.invoke(
            {"question": question, "db_id": db, "trace_id": f"ask-{thread}",
             "top_k": 6, "max_attempts": 3, "difficulty": 3,
             "hitl": True,   # ★ 演示链路：clarify 走 interrupt 挂起等人答
             "attempts": 0, "escalated": False, "sql_history": [],
             "verify_retried": False,
             "behavior": "answer", "cost_cny": 0.0, "in_tokens": 0, "llm_calls": 0},
            config=cfg)

    if tracer is not None:
        tracer.close()

    # langgraph 1.x：被 interrupt 挂起时，结果 dict 里带 __interrupt__ 键
    interrupts = final.get("__interrupt__")
    if interrupts:
        rprint(f"[yellow]Agent 反问：{interrupts[0].value['clarifying_question']}[/yellow]")
        rprint(f'继续：ask --thread {thread} --resume "你的回答"')
        return
    rprint(final.get("answer_text"))
    rprint(f"SQL: {final.get('sql')}")
    rprint(f"(llm_calls={final.get('llm_calls')}, cost=¥{final.get('cost_cny', 0):.4f})")


if __name__ == "__main__":
    app()
