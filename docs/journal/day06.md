# Day 6

## 目标完成度

- [x] composer 自然语言结论生成：`terminal_nodes.py` 补 `COMPOSE_USER`（带 `{columns}` 占位 + "点名实体/数值"要求），`sample` 改为带表头，`answer_text` 全链路打通（pipeline → runner → results.jsonl → review_sheet）
- [x] `a0.py` `SYSTEM` 加"排名口径"硬规则（前 N 名默认 `ROW_NUMBER()`，禁用 `RANK()`/`DENSE_RANK()`，tie-breaker 显式化），从根上压住排序窗口函数摇摆
- [x] verifier 降级：砍 LLM judge，只留 `deterministic_flags` 零成本 guard，`node_verify` 不再调 `client.chat_json`
- [x] tracer + trace_viewer 落地：`obs/tracer.py`（加线程锁）、`obs/trace_viewer.py`（按 question 归组）、`client.py`/`graph.py`/`cli.py` 三处接入，`ask --trace` 可产调用树
- [x] Streamlit 单页 `app.py` 落地（结论/SQL/结果表/成本四区，三库切换）
- [x] 改 prompt 后全量重跑（`v2_{db}_{cfg}`，prompt 指纹 `c1038e268edf` 与当前代码一致）
- [ ] `reports/ablation.md` 未同步到 v2 数据（脚本输出写到 `v2_ablation.md`，正式报告还是旧 `{db}_{cfg}` 数字）
- [ ] README.md 仍 0 字节（Day 6 §4.3 列为"必须做"，未做）
- [ ] review_sheet 30 条**未勾**（人工抽评未执行）
- [ ] Dockerfile/.dockerignore 未建（用户确认"工程化做到本地能跑即可"，Docker 可砍）

## 消融矩阵（v2 数据，prompt 指纹 `c1038e268edf`，三库数据集指纹与 Day 5 一致）

| 库 | 配置 | EX | 首轮EX | 修复增益 | 召回率 | 行为正确率 | gate误杀 | verify修复 | verify误杀 | ¥/题 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| chinook | a0 | 75.0% | — | — | — | 0% | 0 | — | — | 0.0041 |
| chinook | a1 | 75.0% | — | — | 87.5% | 0% | 0 | — | — | 0.0043 |
| chinook | a2 | 70.8% | 70.8% | 0.0% | 87.5% | 0% | 0 | 0 | 0 | 0.0087 |
| chinook | a3 | 83.3% | 79.2% | 4.2% | 91.7% | 83.3% | 0 | 0 | 0 | 0.0105 |
| chinook | a4 | 79.2% | 75.0% | 4.2% | 91.7% | 83.3% | 0 | 0 | 0 | 0.0145 |
| sakila | a0 | 72.2% | — | — | — | 0% | 0 | — | — | 0.0042 |
| sakila | a1 | 55.6% | — | — | 66.7% | 0% | 0 | — | — | 0.0064 |
| sakila | a2 | 66.7% | 66.7% | 0.0% | 77.8% | 0% | 0 | 0 | 0 | 0.0138 |
| sakila | a3 | 72.2% | 66.7% | 5.6% | 66.7% | 100% | 0 | 0 | 0 | 0.0150 |
| sakila | a4 | 66.7% | 61.1% | 5.6% | 83.3% | 100% | 0 | 0 | 0 | 0.0125 |
| ecommerce | a0 | 88.4% | — | — | — | 0% | 0 | — | — | 0.0045 |
| ecommerce | a1 | 81.4% | — | — | 83.7% | 0% | 0 | — | — | 0.0050 |
| ecommerce | a2 | 83.7% | 79.1% | 4.7% | 88.4% | 0% | 0 | 0 | 0 | 0.0079 |
| ecommerce | a3 | 90.7% | 81.4% | 9.3% | 93.0% | 76.5% | 0 | 0 | 0 | 0.0097 |
| ecommerce | a4 | 86.1% | 79.1% | 7.0% | 90.7% | 70.6% | 0 | 0 | 0 | 0.0080 |

## 三个结论

1. **verifier 降级是正确的工程决策，且被 v2 数据证实。** 降级（砍 LLM judge、只留 deterministic_flags）后重跑，chinook_a3 EX 79.2%→83.3%、ecommerce_a3 81.4%→90.7%，sakila 持平 72.2%。EX 不降反升（或持平），说明 LLM judge 不仅零收益，其非确定性甚至还在扰动结果。砍掉后省下的 verify token 是真金白银——这正是 Day 5 §0.5 悬而未决的债，今天按"降级"方案还清了。

2. **composer 自然语言结论让"错误自信率"第一次有了落地基础。** 修复前 composer 输出是"结果前 10 行 dump"，无法产生"过度断言"；补 `{columns}` 后 `ask` 能输出"奥地利 Astrid Gruber 42.62、巴西 Luís Gonçalves 39.62"这类真正回答问题的结论。`make_review_sheet.py` 重跑后 30 条**每一条都有了"结论"字段**，人工终于能勾"是否有过度自信"。但**勾选本身还没做**（30 条全 `[ ]`），这是 Day 7 的第一件事。

3. **排名口径硬规则压住了窗口函数摇摆。** 加"前 N 名默认 ROW_NUMBER()"后，同一个"每个国家前 5 名"问题不再在 RANK/ROW_NUMBER 间摇摆，SQL 稳定、结论无病句。这印证了 Day 5 反复出现的"排序题并列口径"是**系统性短板**，根治办法是把语义约束显式化进 prompt，而不是逐题打补丁。

## 今天修掉的 bug

1. **composer 漏传列名 → 空洞结论**：`sample = "\n".join(str(tuple(r)) for r in rows[:10])` 拼裸元组，`columns` 没进 `COMPOSE_USER`，模型面对无表头数据只能瞎猜，输出"消费额介于 37.62 至 42.62"这类空洞范围。修法：`sample` 改带表头 + `{columns}` 传进 format。
2. **RANK 并列溢出 → SQL 错 + 结论病句**：模型把"前 5 名"用 `RANK()` 实现，并列导致"前 5 名"实际多于 5 人（Canada 8 人、USA 7 人），结论出现"巴西第 2 名均为 37.62"病句。修法：`a0.SYSTEM` 加排名口径硬规则。
3. **checkpoint 污染 → llm_calls 虚高**：`ask` 反复用默认 `thread_id="cli-default"` 导致 langgraph 恢复旧执行历史，`llm_calls` 从 3 累加到 15。教训：演示/评测每次用唯一 thread_id 或换新 checkpoint 文件。

## 已知局限

- **v2_ecommerce_a0 EX=88.4%，又踩了 headroom 红线（>85%）**。chinook(75.0%)、sakila(72.2%) 都达标，唯独 ecommerce 越线 3.4pt。根因：ecommerce 41 道 difficulty=3 题里 A0 只错 5 道，说明"难题"实际不够难——模型 A0 就能答对 36/41。这不是数据脏，是 ecommerce 的"难点"没有真正卡住 A0 基线（CTE/窗口/递归这些对当前模型已不是门槛）。Day 7 需决策：接受 88.4% 并诚实标注，或再加真正卡 A0 的题。
- **`reports/ablation.md` 仍是旧数据**：`ablation_report.py` 的 `RUNS` 已改成 `v2_{db}_{cfg}`，但输出路径写死 `reports/v2_ablation.md`，正式 `ablation.md` 没同步，仍显示 Day 5 的旧数字。Day 7 要把正式报告统一到 v2。
- **错误自信率数字仍未产出**：review_sheet 有结论字段了，但 30 条人工抽评未勾，错误自信率 = 未勾数/30 还没算出来。
- **README 0 字节**：Day 6 §4.3 明确列为"必须做、非可砍"，但未做。这是面试简历链接点开第一眼的东西，Day 7 必须补。

## 明天（Day 7）第一件事

按 `docs/day7-handbook.md` 收尾：① 勾完 review_sheet（产出错误自信率数字）→ ② 统一 ablation.md 到 v2 + 决策 ecommerce headroom → ③ 写 README → ④ 填 design.md / failure_cases.md → ⑤ 简历 + 面试自问。
