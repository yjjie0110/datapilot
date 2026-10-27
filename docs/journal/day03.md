# Day 3

## 目标完成度
- [x] LangGraph 主图（8 节点：retrieve/generate/validate/execute/diagnose/repair/give_up/compose）
- [x] 修复环 + escalate 检索扩大通道（diagnose 就地置位 escalated、计入 attempts）
- [x] SqliteSaver checkpointer 接入（per-thread 文件 + thread_id 带 uuid）
- [x] runner 对接：ex_first / repair_gain / n_escalated 三指标
- [x] A2 × chinook/sakila 两组全量 run（v3 为干净数据）
- [x] 40 单测全绿

## 对比表（run 后缀 _v3，A1 取 _fix 组）

| 库 | run | EX | 首轮 EX | 修复增益 | n_escalated | 召回率 | ¥/题 | avg llm_calls |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| chinook | A1(k=6) | 91.67% | — | — | — | 91.67% | 0.00312 | 1.0 |
| chinook | A2 | 91.67% | 91.67% | 0 | 0 | 91.67% | 0.00315 | 1.0 |
| sakila | A1(k=6) | 83.33% | — | — | — | 72% | 0.00556 | 1.0 |
| sakila | A2 | **88.89%** | 83.33% | **+0.0556** | 1 | 77.78% | 0.00457 | 1.1 |

## 三个结论

1. **修复增益在 sakila 上真实兑现（+5.56pt），标杆案例 sa-015**：首轮 top_k=6 漏表 → 空结果 → LLM 判可疑 → escalate 退回全量 schema → 重生成 → 正确。该题 ex_first=False、ex=True、llm_calls=3、单题成本 ¥0.0082（约 2.6 倍于单发）——修复不是免费的，增益与成本都可量化。
2. **chinook 上修复增益为 0，原因是结构性的**：残留失败（ch-021/022）全是"非空错结果"——SQL 执行成功、返回行数正常、直接走到 compose，diagnose 从根上就没被触发。修复环只能修"看得见的失败"（报错/空结果），修不了"看起来成功的错答案"。这不是调参能解决的，是 Day 4 verifier 的靶子。
3. **behavior_ok=0（6 道 clarify/refuse 题全被硬答）**：A2 没有行为决策能力，歧义题（ch-027）甚至被 escalate 白烧了一轮全量 schema 生成。对抗题里模型直接编造答案（ch-030 编造 USA 归一化逻辑）。修复环的方向是"把 SQL 修对"，管不了"这题该不该答"——Day 4 gate 的靶子。

## 今天修掉的 bug（都是真问题，按发现顺序）

1. `classify_error` 签名与测试错位 + 丢失文本兜底 → 改为 `(err, error_code=None)` 双通道
2. SqliteSaver API 漂移：`from_conn_string` 返回上下文管理器；compile kwarg 是 `checkpointer=`
3. **全图没人写 `attempts`/`sql_history`** → 死循环只能靠递归上限崩溃兜底；改在 diagnose（失败漏斗）统一计数
4. **没有节点置 `escalated=True`** → escalate 空转；改在 diagnose 决定 escalate 时就地置位
5. `src.datapilot.*` 与 `datapilot.*` 混用 → 模块双重加载（settings/缓存各两份）
6. thread_id 无唯一后缀 → 重跑同题复用旧 checkpoint，first_rows/escalated 泄漏
7. **Reducer 缺失**（v1 数据暴露）：cost_cny/in_tokens/llm_calls 被节点互相覆盖，sa-015 实际 3 次调用只记 1 → state.py 三个累加字段挂 `Annotated[_, operator.add]`
8. **SQLite checkpoint 并发锁**（v2 数据暴露）：4 线程共写一个 checkpoints.db → `database is locked` / `readonly database` 共 4 题报废 → 改为 per-thread 文件
9. 手册 6.2 snippet 参数错误（`order_sensitive=` 应为 `ordered=`；settings 无 round_ndigits/casefold——ex 与 ex_first 必须共用默认归一化口径）

## 已知局限

- v1/v2 两组 run 数据作废（记账失真 / 并发锁），结论以 v3 为准；旧 run 封存不删，作为 bug 案例
- 模型有运行间波动：ch-027 在 v1 触发 escalate、v3 没有；sa-015 三次运行都触发（稳定案例）
- 修复增益样本量 n=1（sakila 18 题分母太小），Day 5 扩题后需复核
- prompt 指纹仍写死 a0.SYSTEM，diagnose/repair 的新 prompt 不在指纹内（已知债）

## 明天（Day 4）第一件事

读 a2_sakila_v3 里 sa-013/014 的完整 SQL 与 gold 的差异——它们是 verifier 要拦截的第一类样本，先想清楚"什么样的校验规则能拦住它们且不误杀正确题"。
