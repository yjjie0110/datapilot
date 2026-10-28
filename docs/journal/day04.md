# Day 4

## 目标完成度

- [x] `nodes/gate.py`：行为前置决策（answer / clarify / refuse），fail-open 纪律
- [x] `nodes/verifier.py`：确定性 flag + LLM judge，**只判不改**
- [x] `nodes/terminal_nodes.py`：compose 产出 answer_text（规则拼装不调 LLM）
- [x] HITL：`node_clarify_wait` + `interrupt` / `Command` resume，CLI `ask --resume` 已验通
- [x] `pipelines/a3.py` + `graph.py` 的 `with_reliability=True` 分支
- [x] 四个新指标落地：gate_false_kill / n_verified / verify_fixed / verify 误杀数
- [x] A3 × chinook/sakila 全量 run（**v3 为合格数据，v2 报废**）
- [x] 51 单测全绿

## 对比表（A3 以 v3 为准；v2 是作废数据，保留作为 bug 案例）

| 库 | 配置 | EX | 首轮EX | 修复增益 | n_esc | 召回率 | 行为正确率 | gate误杀 | verify修复 | 误杀 | 均token | ¥/题 | P95(s) | llm |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| chinook | A1(k=6) | 91.67% | — | — | 0 | 91.67% | 0% | — | — | — | 896 | 0.00312 | 61 | 1.00 |
| chinook | A2 | 91.67% | 91.67% | 0% | 0 | 91.67% | 0% | — | — | — | 891 | 0.00314 | 45 | 1.00 |
| chinook | A3 v2 | 95.83% | 91.67% | 4.17% | 0 | 91.67% | 83.33% | 0 | 0 | 0 | 2234 | 0.00667 | 120 | 2.40 |
| chinook | **A3 v3** | **95.83%** | 91.67% | **4.17%** | 1 | 95.83% | **83.33%** | 0 | 0 | 0 | 2252 | 0.00572 | 76 | 2.33 |
| sakila | A1(k=6) | 83.33% | — | — | 0 | 72.22% | 0% | — | — | — | 979 | 0.00556 | 124 | 1.00 |
| sakila | A2 | 88.89% | 83.33% | 5.56% | 1 | 77.78% | 0% | — | — | — | 1041 | 0.00457 | 95 | 1.10 |
| sakila | A3 v2 | 72.22% | 72.22% | 0% | 0 | 72.22% | 100% | 1 | 0 | 0 | 2608 | 0.01030 | 1290 | 2.60 |
| sakila | **A3 v3** | **83.33%** | 83.33% | 0% | 1 | 77.78% | **100%** | 1 | 0 | 0 | 2602 | 0.00667 | 93 | 2.40 |

## 三个结论

1. **A3 唯一的实质收益是"行为决策"，不是答案质量。** chinook 特殊题正确率 0% → 83.33%，sakila 0% → 100%，8 道 clarify/refuse 题几乎全对——这是 A2 完全不具备的能力（当时 6 道全被硬答）。而 EX 侧：chinook +4.17pt，sakila −5.56pt（1 题，且这题是 gate 误判而非 SQL 能力），**两者都在 18–24 题分母的波动范围内**，不能说 A3 让模型变聪明了。
2. **verifier 至今零收益，这是必须写进报告的负结果。** 三组 run 的 `verify_fixed` 全是 0、`verify 误杀` 全是 0——verifier 拦到了 sa-015（判 `wrong`）但修复没跟上，其他题全部 pass。它买到的是"没有误伤"，不是"多答对"，代价是 token +150%、单题成本 +46%~82%。**结论不是"它有用"，而是"它的收益形态还没兑现"，Day 5 扩到第三库后按决策树给出存废答案。**
3. **组件之间存在非平凡耦合，这是今天最有价值的工程发现。** 加了 verify 之后，失败形态从"报错/空结果"被改写成了"带毒的非空结果"，而 `wrong_result` 当时只走 repair、从不 escalate —— 结果 sa-015 在 A2（无 verify）能靠 escalate 修好，到 A3（有 verify）反而修不动了。**可靠性组件不是可以独立插拔的积木，它们会互相改变对方的输入分布。** 这条比任何一个 +Xpt 都更值得在面试里讲。

## 今天修掉的 bug（按发现顺序）

1. **graph.py 的 execute 条件边注册两次**：`if with_reliability` 块内一次、块外残留一次 → 同一源节点重复注册 Branch，compile 直接 ValueError，A2 也跑不了
2. **三个路由函数只被引用未定义**：`_route_after_gate` / `_route_after_execute_reliability` / `_route_after_verify`，A3 首次构图必 NameError
3. **`src.datapilot.*` 前缀反复复发**：a3.py / cli.py / gold_tables.py 三处，双模块实例（Day 3 的教训又犯了两次）
4. **gate 误拒 demo 题（结构性缺陷，非笔误）**：gate 用"检索后的部分 schema"判 refuse，而 refuse 需要"全库都没有"的完备知识。检索漏表（中文"歌单"召不回 `Playlist`）被 gate 放大成误拒，本可自愈的 escalate 链被提前判死 → 【方案 A】prompt 增加全库紧凑表清单（约 200 token），refuse 的唯一依据改为该清单
5. **`wrong_result` 触发不了 escalate（本次最致命）**：修前 sakila 从 88.89% 崩到 72.22%，sa-015 在 A2 修好、A3 修不动；修后回升到 83.33%，sa-015 恢复正确
6. **gate 拦截被记成 `sql_error`**：a3.py 用 `exec_ok` 判 status，而 clarify/refuse 从未执行过 SQL → error_rate 被行为误判污染（sakila 谎报 5.56%）。改为 `clarified` / `refused` 独立状态
7. **metrics 的 error_rate 口径跟着错**：`status != "ok"` 把 clarified/refused 也算成 SQL 错误 → 收紧为 `status in ("sql_error","error")`
8. **Day 5 手册的 a4.py 沿用了 a3 的错误 status 写法** → 同步修掉（手册与实现必须同版本）
9. report.py 汇总表缺四个新指标行 → 补齐

## 已知局限

- **v2 数据作废**（bug 5/6/7 未修），结论以 v3 为准；旧 run 封存不删，作为 bug 案例
- **模型运行间波动实测存在**：sa-004 在 A2=True / A3v2=False / A3v3=True 三连翻转，同一 temperature=0、同一 prompt、同一输入，纯模型侧不确定性。这意味着**本项目任何单次 run 的 EX 都有 ±1 题（±4pt）的噪声**，两次 run 差 1 题不许下结论
- `prompt_fingerprint()` 仍写死 a0.SYSTEM——gate/verify/repair 的 prompt 不在指纹内，改了它们不会阻止续跑，属已知债（Day 4 就是靠手改 run_id 后缀规避的）
- verify 的成本门控规则（`difficulty < 3 且无 flags` 免调 LLM）让 chinook 有相当比例题目根本没真正过 judge，`n_verified` 计数口径是"进过 verify 节点"，不等于"用过 LLM judge"，读数字时要注意
- gate 的 clarify 门槛偏松：sa-003（题面已给全排序+取数口径）被判 clarify 丢题；fail-open 纪律目前只覆盖解析失败/非法 action，没覆盖"answer vs clarify 拿不准"

## 明天（Day 5）第一件事

按 `docs/day5-handbook.md` §0.5 的两个待决事项先想清楚：**① verifier 存废的三条命运**（保留观察 / 降级为纯确定性 guard / 改造为 escalate 触发源），**② gate 的 clarify 门槛收紧一句话**。然后才动第三库的建库脚本——电商 schema 是今天全部结论的"是否被训练语料污染"的唯一检验。
