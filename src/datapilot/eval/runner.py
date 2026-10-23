# 这是 Text-to-SQL 项目的评测运行器（Evaluation Runner）。
# 核心职责是：把评测数据集逐题喂给 pipeline，并发执行、逐条打分、增量落盘、支持断点续跑，最后汇总成指标报表。
# 一句话：它是整个评测流水线的"总调度"——score_one 负责判一道题，run_eval 负责把几百道题高效、可靠、可恢复地跑完。


from __future__ import annotations

import hashlib
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock
from typing import Callable

from datapilot.config import settings
from datapilot.eval.metrics import aggregate, explain_mismatch, results_equal

from datapilot.eval.eval_config import config_fingerprint, load_eval_config

# 多线程写文件的互斥锁
_write_lock = Lock()


# 读 JSONL
# 一次读入内存。对评测数据集（通常几百到几千条）足够；若换成百万级需改成流式
def load_dataset(path: str | Path) -> list[dict]:
    p = Path(path)
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


# 运行可比性标记
def prompt_fingerprint() -> str:
    """把 prompt 的哈希写进 meta，防止拿两次不可比的 run 做对比。"""
    try:
        # 取 pipeline 的 system prompt，算 SHA256 前 12 位，写进 meta.json
        # 目的：两次 run 的 prompt 不同 → 结果不可直接对比。有了指纹，报表工具可以拒绝"拿不同 prompt 的 run 做对比"；
        from datapilot.pipelines import a0
        return hashlib.sha256(a0.SYSTEM.encode("utf-8")).hexdigest()[:12]
    except Exception:
        return "na"


def get_pipeline(cfg: dict) -> Callable[[dict], dict]:
    """按 cfg["pipeline"] 分发，并把 cfg 里的参数绑定进 pipeline 调用。"""
    name = cfg["pipeline"]
    if name == "a0":
        from datapilot.pipelines.a0 import a0_answer
        return lambda q: a0_answer(q)
    if name == "a1":
        from datapilot.pipelines.a1 import a1_answer
        top_k = cfg.get("top_k", 6)
        return lambda q: a1_answer(q, top_k=top_k)
    if name == "a2":
        from datapilot.pipelines.a2 import graph_answer
        return lambda q: graph_answer(q, cfg=cfg)
    raise ValueError(f"未知 pipeline：{name}")


# 单题评分（核心）负责判一道题
def score_one(q: dict, pipeline_fn: Callable[[dict], dict]) -> dict:
    """输入一道题 + pipeline 函数（a0_answer......），输出一条完整记录。"""
    # 用于基准测试的性能计数器。(高精度计时）
    t0 = time.perf_counter()
    # 关键设计：单题失败不中断整个评测，降级为 status="error" 记录。这让 1000 题里挂 3 题也能跑完全程。
    try:
        # return {"status": ,"sql": ,"tables_used": ,"assumptions": ,"rows": ,"columns": ,"error": ,
        #           "error_code": ,"behavior": ,"llm_calls": ,"cost_cny": ,}
        out = pipeline_fn(q)
        err = None
    except Exception as e:
        out = {
            "status": "error", "sql": None, "rows": None, "behavior": "answer",
            "llm_calls": 0, "cost_cny": 0.0,
        }
        err = f"{type(e).__name__}: {e}"

    # 取预测行、gold 行、行为
    rows = out.get("rows")  # 经过llm 产生sql 获取的pre
    gold = q.get("gold_result")  # chinook_v0.jsonl 中的gold_result
    behavior = out.get("behavior", "answer")

    # 只有 expected_behavior == "answer" 的题才算 EX；special 题 ex = None，正确
    ex = ex_ord = None
    if q["expected_behavior"] == "answer":
        if out.get("status") == "ok" and rows is not None and gold is not None:
            # 计算EX
            ex = results_equal(rows, gold)
            # 逐行严格比较
            ex_ord = (
                results_equal(rows, gold, ordered=True)
                if q.get("order_sensitive")
                else None
            )
        else:
            ex = False
            # 失败兜底也要尊重 order_sensitive 标记，否则 aggregate 会把所有
            # answerable 题都算进排序题分母（全 error 的 run 里 n_order_sensitive 会虚高）
            ex_ord = False if q.get("order_sensitive") else None

    # 只在"判错了且两边都有数据"时生成人话版差异
    mismatch = None
    if ex is False and rows is not None and gold is not None:
        mismatch = explain_mismatch(rows, gold)

    # 召回率：仅 answer 题、且 pipeline 上报了检索结果时有意义
    extra = dict(out.get("extra") or {})
    if (
        q["expected_behavior"] == "answer"
        and out.get("retrieved_tables") is not None
        and q.get("gold_tables")
    ):
        extra["schema_recall"] = int(
            set(q["gold_tables"]) <= set(out["retrieved_tables"])
        )

    # 记录字段设计比较完整：题目元信息、行为、状态、SQL、行数、EX、差异、错误、延迟、LLM 调用、成本
    return {
        "id": q["id"],
        "question": q["question"],
        "question_type": q["question_type"],
        "difficulty": q.get("difficulty"),
        "expected_behavior": q["expected_behavior"],
        "behavior": behavior,
        "behavior_ok": behavior == q["expected_behavior"],
        "status": out.get("status", "unknown"),
        "sql": out.get("sql"),
        "tables_used": out.get("tables_used"),
        "row_count": len(rows) if rows is not None else None,
        "order_sensitive": bool(q.get("order_sensitive")),
        "ex": ex,
        "ex_ordered": ex_ord,
        "gold_tables": q.get("gold_tables"),
        "retrieved_tables": out.get("retrieved_tables"),
        **extra,
        "mismatch": mismatch,
        "error": err or out.get("error"),
        "latency_ms": round((time.perf_counter() - t0) * 1000),
        "llm_calls": out.get("llm_calls", 0),
        "cost_cny": out.get("cost_cny", 0.0),
    }


def dataset_fingerprint(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:12]

# 续跑添加数据集指纹
def run_fingerprint(dataset_path: str | Path, cfg: dict) -> str:
    """三段式指纹：数据集 + prompt + 评测配置。任何一段变了都不许续跑。"""
    return (
        f"{dataset_fingerprint(dataset_path)}"
        f"-{prompt_fingerprint()}"
        f"-{config_fingerprint(cfg)}"
    )


# 负责把几百道题高效、可靠、可恢复地跑完
def run_eval(
    *,
    config_name: str,
    dataset_path: str | Path | None = None,
    run_id: str | None = None,
    limit: int | None = None,
    concurrency: int | None = None,
) -> dict:
    cfg = load_eval_config(config_name)      # 配置即实验身份
    pipeline_fn = get_pipeline(cfg)          # 按 cfg 分发并绑定
    dataset_path = Path(dataset_path or settings.dataset)  # 数据集路径jsonl
    run_id = run_id or f"{config_name}_{time.strftime('%Y%m%d_%H%M%S')}"  # 输出结果id
    run_dir = Path(settings.run_dir) / run_id  # 输出结果文件夹
    run_dir.mkdir(parents=True, exist_ok=True)
    res_path = run_dir / "results.jsonl"

    fp = run_fingerprint(dataset_path, cfg)
    meta_path = run_dir / "meta.json"

    # ---- 续跑：已经算过的题直接跳过 ----
    if res_path.exists() and meta_path.exists():
        old = json.loads(meta_path.read_text(encoding="utf-8"))
        if old.get("fingerprint") and old["fingerprint"] != fp:
            raise RuntimeError(
                f"数据集、prompt 或评测配置已变化（{old['fingerprint']} -> {fp}）。"
                f"请换一个 run_id，或删除 {run_dir}。"
            )

    done: set[str] = set()
    if res_path.exists():  # 读已有 results.jsonl，收集已完成的 id
        for line in res_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                done.add(json.loads(line)["id"])

    # 读取数据集chinook_v0.jsonl 中的每一行
    items = [q for q in load_dataset(dataset_path) if q["id"] not in done]
    if limit:  # 截取前limit 条
        items = items[:limit]

    # 写运行元信息，字段覆盖 run 标识、配置、数据集、进度、关键参数
    meta = {
        "run_id": run_id,
        "config": config_name,
        "prompt_fingerprint": prompt_fingerprint(),
        "fingerprint": fp,
        "eval_config": cfg,  # 完整配置落盘（含 top_k / repair_max_attempts）
        "model": settings.model,
        "base_url": settings.base_url,
        "temperature": settings.temperature,
        "dataset": str(dataset_path),
        "n_pending": len(items),
        "n_already_done": len(done),
        "started_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "max_rows": settings.max_rows,
        "sql_timeout_s": settings.sql_timeout_s,
    }
    (run_dir / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    if items:
        # 创建线程池，max_workers 取 concurrency（函数参数）和 settings.concurrency（全局配置）中第一个真值
        # 追加模式，续跑时保留旧结果
        with ThreadPoolExecutor(concurrency or settings.concurrency) as pool, open(
            res_path, "a", encoding="utf-8"
        ) as sink:
            # 对 items 中每道题 q，提交一个任务到线程池执行 score_one(q, pipeline_fn)
            # ⚠️ 潜在风险：如果 items 极大（几十万），所有任务会一次性入队，Future 对象也全部驻留内存。更稳健的写法是用 executor.map 或分批提交
            futures = [pool.submit(score_one, q, pipeline_fn) for q in items]

            # as_completed(futures)是一个生成器，按任务完成的先后顺序 yield 出 Future（不是提交顺序！）
            for i, fut in enumerate(as_completed(futures), 1):  # i 从1开始计数
                # 阻塞取结果：Future.result() 在任务完成时返回 score_one 的返回值（此处应为 dict，字段含 id、status、ex 等）
                # 由于 as_completed 只在任务已完成后才 yield，所以此处的 result() 不会阻塞，直接返回值
                rec = fut.result()

                # 目的：保证写文件的临界区原子性。
                # 实际上这里是冗余的：主线程是唯一消费 futures 的线程，写文件本身已串行。加锁更多是防御性编程——防止将来有其他线程（比如在 score_one 里或日志线程）也写同一个 sink。
                # 若 _write_lock 是 threading.Lock，则不可重入；若是 RLock 可重入。这里只需普通 Lock。
                with _write_lock:
                    # 把记录序列化成 JSON 字符串在写入"results.jsonl"里
                    sink.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    sink.flush()  # 关键：进程崩了也不丢已完成的题
                # 打印进度：[已完成/总数]，配合 as_completed 的乱序完成，进度是"真进度"
                print(f"[{i}/{len(items)}] {rec['id']} status={rec['status']} ex={rec['ex']}")

    # 获取"results.jsonl"里的记录
    records = [
        json.loads(l)
        for l in res_path.read_text(encoding="utf-8").splitlines()
        if l.strip()
    ] if res_path.exists() else []
    return {
        "run_id": run_id,
        "run_dir": str(run_dir),
        "summary": aggregate(records),
        "records": records,
    }
