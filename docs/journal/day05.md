# Day 5

## 目标完成度

- [x] 第三库 ecommerce.db 建成（12 表，seed=42 确定性可复现），GMV 冒烟可算
- [x] `ecommerce_glossary.md` 业务口径落盘
- [x] `ecommerce_v0.jsonl` 60 题，verify-gold 无截断警告，gold_tables 已回填，≥2 道 CTE 题
- [x] A4 = A3 + 缓存 + 路由：`llm/cache.py`、`client.py` 三处接入、`config.py` model_small、`common_nodes.py` 路由、`graph.py` 按缓存分键、`state.py` route_small、`a4.yaml`、`pipelines/a4.py` 全部落地
- [x] chinook / sakila 评测集重构（加难度 3 的题），三库 A0 全部 < 85%（headroom 成立）
- [x] gate clarify 门槛收紧（§0.5 欠债还清），gate 误杀三库归零
- [x] 15 个 run（A0–A4 × 3 库）全部重跑、0 error、数据集指纹与评测集逐字节一致
- [x] `reports/ablation.md` 重新生成，15 run 全覆盖
- [x] 修掉 prompt_fingerprint 漏项（GATE_USER 未纳入指纹）
- [ ] `reports/review_sheet.md` 已生成 30 条但**未勾完**——结论文本缺失，见"已知局限"

## 消融矩阵（数据可溯源到 run_id，三库均为重构后数据集）

| 库 | 配置 | EX | 首轮EX | 修复增益 | 召回率 | 行为正确率 | gate误杀 | verify修复 | verify误杀 | ¥/题 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| chinook | a0 | 79.2% | — | — | — | 0% | 0 | — | — | 0.0037 |
| chinook | a1 | 75.0% | — | — | 87.5% | 0% | 0 | — | — | 0.0039 |
| chinook | a2 | 70.8% | 70.8% | 0% | 87.5% | 0% | 0 | 0 | 0 | 0.0030 |
| chinook | a3 | 79.2% | 75.0% | 4.2% | 91.7% | 83.3% | 0 | 0 | 0 | 0.0054 |
| chinook | a4 | 79.2% | 75.0% | 4.2% | 95.8% | 83.3% | 0 | 0 | 0 | 0.0011 |
| sakila | a0 | 72.2% | — | — | — | 0% | 0 | — | — | 0.0035 |
| sakila | a1 | 61.1% | — | — | 66.7% | 0% | 0 | — | — | 0.0062 |
| sakila | a2 | 66.7% | 61.1% | 5.6% | 77.8% | 0% | 0 | 0 | 0 | 0.0064 |
| sakila | a3 | 72.2% | 61.1% | 11.1% | 83.3% | 100% | 0 | 0 | 0 | 0.0084 |
| sakila | a4 | 72.2% | 66.7% | 5.6% | 77.8% | 100% | 0 | 0 | 0 | 0.0077 |
| ecommerce | a0 | 79.1% | — | — | — | 0% | 0 | — | — | 0.0038 |
| ecommerce | a1 | 67.4% | — | — | 83.7% | 0% | 0 | — | — | 0.0042 |
| ecommerce | a2 | 69.8% | 65.1% | 4.7% | 90.7% | 0% | 0 | 0 | 0 | 0.0047 |
| ecommerce | a3 | 81.4% | 72.1% | 9.3% | 95.3% | 76.5% | 0 | 0 | 0 | 0.0065 |
| ecommerce | a4 | 81.4% | 72.1% | 9.3% | 97.7% | 76.5% | 0 | 0 | 1 | 0.0061 |

## 三个结论

1. **A0 全库 < 85% 后，消融曲线终于有了"可分空间"，且形态健康。** 重构前 chinook A0=95.8%、sakila A0=100%，A1–A4 全在 A0 之下或持平，"增益"无意义。加难度 3 题后三库 A0 落在 72–79%，曲线变成清晰的"检索引入损失（A1 降）→ 修复环回补（A2/A3 升）→ A3/A4 到顶"。**这是消融矩阵第一次讲得出完整故事**：检索的代价是漏召砍 EX，修复/校验/扩检索再把它拉回来。ecommerce 是唯一 A3>A0 的库（81.4% vs 79.1%），说明可靠性组件在"模型没背过的自建库"上收益最实在——这正是第三库存在的价值。

2. **gate 收紧后误杀归零，但 behavior_ok 未崩——fail-open 纪律第一次被真正兑现。** 收紧 clarify 门槛（口径已给就判 answer）后，三库 gate_false_kill 全部从 6/8 降到 0，而 chinook 83.3%、sakila 100%、ecommerce 76.5% 的特殊题正确率没有因为"放水"而塌。之前 gate 是"宁可反问也不错答"，现在是"口径明确就答"，这个 shift 是 Day 4 留下的债，今天还清了。

3. **verifier 依然是零收益（三库 verify_fixed 全 0），但这次多了一个"误杀"样本，结论可以收口了。** ecommerce_a4 的 ec-042 是首个 `ex_first=True → ex=False` 的样本（verify 判 pass 未拦，gold 口径是"商品数"、模型算成"库存件数"）。按 §3 决策树：三库"错误自信"样本合计不足 5 题，**样本检验力不足，不许下"verifier 有效/无效"的结论**，只能如实写"当前评测集对该组件的检验力不足"，列为已知局限。verifier 的存废按"降级"方案处理：砍 LLM judge，只留 deterministic_flags 做零成本 guard。

## 今天修掉的 bug

1. **A4 全 error（缓存目录不存在）**：`LLMCache.__init__` 直接 `sqlite3.connect("experiments/cache/llm_cache.db")`，父目录不存在 → `unable to open database file`。A3 不碰缓存所以没事，A4 一开 `cache:true` 就 6 题全挂。修法：连接前 `Path(path).parent.mkdir(parents=True, exist_ok=True)`。
2. **prompt_fingerprint 漏掉 GATE_USER**：指纹只拼了 `a0.SYSTEM / repairer / diagnoser / gate.GATE_SYSTEM / verifier`，漏了 `gate.GATE_USER`。改 gate 的 clarify 门槛后指纹不变，旧 run_id 可静默续跑混入两套结果。已把 `GATE_USER` 纳入 parts。

## 已知局限

- **"错误自信率"人工抽评无法真正执行**：`node_compose` 的 `answer_text` 是规则拼装（SQL 结果前 10 行直接 dump），不是 LLM 生成的自然语言结论，因此不会产生"相关当因果""样本当全体"这类断言。`make_review_sheet.py` 抽出的 30 条只有 SQL + 行数，没有结论文本可勾。**结论：当前系统的"结论"是结果集的机械转述，不存在"过度自信"的语义空间——错误自信率这个指标在本项目形态下天然为 0，不是好消息，是 composer 还没做"自然语言结论生成"。**
- **chinook_a2（70.8%）比 a1（75%）还低**：ch-004 一题被修复环改错（或未救回），单题 ±4pt 波动，样本小不构成"修复有害"的结论，但要在面试里如实说"修复环在 chinook 上未产生正收益"。
- **A1 检索三库全比 A0 低**（-4~-11pt）：BM25 漏召是 A1 的结构性代价，是 A2/A3 修复增益存在的前提，不是 bug，但要在报告里写清"检索省 token 的代价是 EX 回退"。
- **sakila 枚举值问题复发**：sa-004 模型猜 `active='Y'`，实际是整数 1/0，与 ecommerce 的 `status='on'` 同源——schema 不带枚举取值是反复出现的系统性短板，列为后续改进项（Day 6+）。
- **ec-042 是 A4 的真实失分**（非 gold 错）：题面已写清"商品总数"，模型误读成"库存件数"（SUM inventory_logs），属语义理解偏误。

## 明天（Day 6）第一件事

按 `docs/day6-handbook.md` 开工：先补 `node_compose` 的自然语言结论生成（这是"错误自信率"指标能落地的唯一前提），再决定 verifier 的"降级"改造，最后收口 README。
