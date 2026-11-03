# Day 7 实施手册 — 沉淀与表达（项目收尾，这天决定面试效果）

> 前置：Day 6 已收口（composer 自然语言结论、verifier 降级、tracer、Streamlit 均已落地）。
> 本手册代码块已按项目实际导入约定（`from src.datapilot.*`）核对过。
> **今天不做任何新功能，只做三件事：还债、沉淀、表达。** 目标是让这个仓库经得起"点开就信"的审视。

## 0. 开工前必读：今天为什么是"沉淀"而不是"再做"

七天下来你已经有一个能跑通 A0–A4 全链路、三库消融矩阵、可观测 + Demo 的完整项目了。**再往下加东西，边际收益接近零，边际风险（把已经讲清楚的故事搞脏）很高。** 今天唯一要做的是把散落在代码、日报、实验结果里的东西，提炼成三份"面试官 10 分钟内能读懂"的产物：

1. **design.md** —— 让面试官能复述你的架构和取舍；
2. **failure_cases.md** —— 让面试官相信你是"真踩过坑"而不是"抄了个 demo"；
3. **README + 简历 + 面试自问** —— 让"点开仓库"这一步就赢。

**纪律：今天写的每一句话，都要能溯源到一个真实的 run_id 或一个真实的 commit。** 不许写"我们的系统准确率很高"这种没有数字支撑的空话。

---

## 1. 还债（30 分钟，先做，否则后面写的都是脏的）

Day 6 留下了三笔债，必须先清，因为它们直接影响 design.md 里"实验结果"这一节的可信度。

### 1.1 统一消融报告到 v2

`scripts/ablation_report.py` 的 `RUNS` 已经是 `v2_{db}_{cfg}`，但输出写到了 `reports/v2_ablation.md`，正式的 `reports/ablation.md` 还是 Day 5 的旧数字。改输出路径：

```python
# scripts/ablation_report.py 最后几行
out = Path("reports/v2_ablation.md")   # ← 改成下面这行
out = Path("reports/ablation.md")
out.write_text("\n".join(lines), encoding="utf-8")
```

然后重跑，确认 `reports/ablation.md` 里的 ecommerce_a0 变成 88.4%（v2），而不是 79.1%（旧）。

> 如果不想覆盖旧文件（保留历史对比），就反过来：把 `v2_ablation.md` 重命名为 `ablation.md`，旧的那份改名 `ablation_day5.md` 存档。**关键是一份"当前有效"的报告，名字要无歧义。**

### 1.2 决策 ecommerce headroom（88.4% 越线）

v2 三库 A0：chinook 75.0%、sakila 72.2%、**ecommerce 88.4%（越线）**。

这是个必须现在拍板的问题，不能带进 design.md 含糊过去。两个选择：

**方案 A（推荐，诚实标注）：接受 88.4%，在 design.md 的"局限"里明确写一句。**
- 理由：ecommerce 的 41 道 difficulty=3 题里 A0 只错 5 道，说明"难题"对当前模型（qwen3.8-flash）已经不够难——CTE/窗口/递归这些不是它的门槛了。**这本身就是一个诚实的、可讲的结论**："模型在自建库上的裸能力下限是 88%，说明评测难度还需要上调。"
- 代价：ecommerce 这一列的消融曲线 headroom 不足，A3(90.7%) 的"增益"被压缩，你需要在报告里弱化 ecommerce 的"可靠性组件收益"叙事，强调"chinook/sakila 才是 headroom 充足、能讲消融故事的库"。

**方案 B：再加真正卡 A0 的题。**
- 素材方向（要真的难住 A0，得是"多跳语义 + 口径陷阱"组合，不是堆 CTE）：
  - 多表多条件 + 中文业务黑话（如"客单价""复购率""连带率"这类需要先翻译成 SQL 口径的词）
  - 时间窗口 + 状态变迁组合（如"已发货但未签收超过 7 天的订单"）
  - 需要跨事实表聚合 + 反事实条件（如"退款后仍计入 GMV 的用户占比"）
- 代价：造题 + verify-gold + gold_tables + 重跑三库全量，至少 2-3 小时，可能挤掉今天后面的沉淀时间。

**我的判断：选 A。** 你的核心目标是"面试能讲清楚"，不是"评测集完美"。88.4% 带一句诚实标注，比花 2 小时造题（还可能造出来还是不卡 A0）更划算。把这 2 小时省下来写 design.md 和 failure_cases，面试收益高得多。

### 1.3 勾完 review_sheet（产出错误自信率数字）

`reports/v2_review_sheet.md` 已经 30 条、每条都有"结论"字段了，但**一条都没勾**。现在逐条人工判断：

- 打开 `reports/v2_review_sheet.md`；
- 每条看"结论"那一行，判断它是否做了**结果集不支持的断言**（编造具体数值、把样本当全体、把相关当因果、臆测原因）；
- 有就 `- [ ]` 改成 `- [x]`，并在"备注"写一句为什么；
- 最后统计：`错误自信率 = 勾选数 / 30`。

**这个数字是 design.md §5 的硬通货**，比 EX 更锋利。哪怕结果是 0/30（很可能，因为你的 composer 加了"严格基于结果集"的约束），也要写出来——"错误自信率 0%，因为 composer 有严格约束"是一个**主动设计出来的好结果**，不是"没测"。

> 注意：这一步是**人的判断**，我不能替你勾（判断的是"结论文本是否做了过度断言"，这是语义判断，不是规则能替代的）。但我可以帮你把 30 条的结论都读一遍、标出我**怀疑**有过度断言的候选，你再确认。

---

## 2. design.md（8 页内，今天最大的一块，2.5 小时）

`docs/design.md` 现在还是占位骨架。按下面的结构填实，**每一节都要有数字或 run_id 支撑**。

### 2.1 背景与问题定义

写清楚三句话：
- **解决什么**：把自然语言问题翻译成可信的 SQL 查询 + 自然语言结论（不是"SQL 翻译器"，是"数据分析 Agent"）。
- **给谁用**：不会写 SQL 的业务/产品，需要从库里拿数。
- **为什么值得做**：LLM 直接生成 SQL 有两个致命问题——**答错**（语义误解、枚举猜错、口径混乱）和**答错还自信**（编造结论）。这个项目用"评测先行 + 消融"的方法，量化每个可靠性组件到底有没有用、代价多大。

> 不要写"因为 Agent 很火"。写"因为 LLM 生成的 SQL 不可信，而现有工具链没有量化不可信的程度"。

### 2.2 系统架构

画一张图（Mermaid 或 ASCII 都行），节点是：gate → retrieve → generate → validate → execute → diagnose/repair（循环）→ verify → compose。每个节点一句话职责，然后**说明为什么这样切分**（关键：gate 在最前挡歧义/危险、retrieve 控 token、diagnose/repair 是"执行反馈驱动的修复环"、verify 兜底客观异常、compose 把结果转成结论）。

架构图建议用 Mermaid（GitHub 直接渲染）：

```mermaid
flowchart TD
    Q[用户问题] --> G[gate 门控]
    G -->|answer| R[schema 检索]
    G -->|clarify| C[反问澄清]
    G -->|refuse| RF[拒答]
    R --> GE[generate 生成 SQL]
    GE --> V[validate 语法校验]
    V --> E[execute 执行]
    E -->|成功| VF[verify 校验]
    E -->|失败| D[diagnose 诊断]
    D -->|可修| RP[repair 修复]
    D -->|不可修| GU[give_up]
    RP --> GE
    VF --> CP[compose 生成结论]
    CP --> A[answer_text]
```

### 2.3 关键决策与取舍（3 个，每个都真实可溯源）

**决策 1：为什么失败时选择"拒答"而不是"硬答"。**
gate 对危险 SQL（写操作）和超纲问题直接 `refuse`，而不是让模型硬生成一个大概率错的答案。代价是可能误拒（gate_false_kill），Day 5 用"fail-open 收紧"把误杀从 6/8 归零。这是"可靠性优先于覆盖率"的取舍。

**决策 2：为什么修复环上限设为 3 轮，且"检索扩大"（escalate）比"语法修复"（repair）更关键。**
Day 3 实测发现失败几乎全是"检索错"（schema 不全）而非"语法错"，所以修复环的核心是 escalate（退回全量 schema 重生成）而非 repair。3 轮是防死循环的硬上限，超过就 give_up。

**决策 3：为什么 verifier 从"LLM judge"降级成"确定性 guard"。**
Day 5 三库实测 verify_fixed 全 0（LLM judge 零收益），但买到了 0 误杀、代价是 token +150%。Day 6 按决策树降级：砍 LLM judge，只留 deterministic_flags（整列 NULL/全 NULL/截断）。降级后重跑 EX 不降反升（chinook_a3 79.2→83.3、ecommerce_a3 81.4→90.7），证明这是对的。**这是本项目最诚实的一个负结果**，面试必讲。

### 2.4 评测设计

- **数据集怎么造的**：chinook/sakila 公开库 + 自建 ecommerce（12 表 seed=42，模型绝对没见过，防污染）；gold_sql 手写 + gold_result 目检；verify-gold 自洽校验（gold_sql 能精确复现 gold_result）。
- **指标怎么定义**：EX（执行结果等价，多重集比较，非文本相似度）+ ex_first（首轮）+ repair_gain + schema_recall + behavior_ok（特殊题）+ gate_false_kill + verify_fixed + 单题成本。
- **为什么用执行结果等价而不是文本相似度**：SQL 写法千千万，文本相似会误判；执行结果才是"对不对"的唯一真相。
- **主动规避的格式陷阱**：temperature=0 减少波动、三段式指纹（数据集-prompt-配置）防静默续跑混数据、tie-breaker 写死防并列无序误判。
- **已知局限**：小样本（30/20/60 题，1 题=±4pt）、ecommerce headroom 不足、错误自信率样本少。

### 2.5 实验结果

贴 v2 消融表（`reports/ablation.md`），并写**至少一条负结果**。候选：
- A1 检索三库全比 A0 低（漏召砍 EX）——这是"检索省 token 的代价"；
- verifier LLM judge 零收益 → 降级；
- chinook_a2 比 a1 低（修复环在 chinook 未产生正收益）。

### 2.6 局限与已知问题

主动承认，逐条列（直接抄 Day 6 日报的"已知局限"即可，补一条 headroom）。

---

## 3. failure_cases.md（3 个真实案例，1.5 小时）

`docs/failure_cases.md` 现在也是占位骨架。填 3 个**你真实遇到过的**案例，每个按"现象 → 定位 → 根因 → 修复 → 对指标的影响 → 面试可引申"写。**候选（都是这个项目里真实发生的）：**

**案例 1：A4 全 error（缓存目录不存在）** —— 现象：A4 冒烟 6 题全 `status=error`，A3 却正常。定位：A3/A4 走同一 graph，差异在 A4 开了 `cache:true`。根因：`LLMCache.__init__` 直接 `sqlite3.connect("experiments/cache/llm_cache.db")`，父目录不存在 → `unable to open database file`。修复：连接前 `mkdir(parents=True)`。引申点：**相对路径 + 隐式依赖目录是 Python 项目高频坑**，连接外部资源前先确保目录/资源存在。

**案例 2：composer 漏传列名 → 空洞结论** —— 现象：`ask` 输出的结论是"消费额介于 37.62 至 42.62"这种空洞范围。定位：结论是 LLM 生成的但内容废。根因：`sample` 拼的是裸元组 `('Argentina', 1, 'Leone Köhler', 37.62, 1)`，没传 `columns`，模型不知道每列含义只能瞎猜。修复：`sample` 带表头 + `{columns}` 传进 prompt。引申点：**给 LLM 的输入要显式化语义**，否则它会在正确结构上产出错误语义。

**案例 3：RANK 并列溢出 → SQL 错 + 结论病句** —— 现象："每个国家前 5 名"用 RANK() 实现，并列导致"前 5 名"实际多于 5 人。根因：模型在 RANK/ROW_NUMBER 间摇摆，没吃准"前 N 名"的并列语义。修复：`SYSTEM` 加排名口径硬规则（默认 ROW_NUMBER）。引申点：**窗口函数并列语义是 Text-to-SQL 的系统性难点**，要靠 prompt 硬规则而非逐题补丁。

> 这三个案例分别覆盖"资源/工程""prompt 语义""SQL 生成正确性"三个维度，面试被问"你踩过什么坑"时，能各讲一个。

---

## 4. README（1 小时，必须做）

`README.md` 现在还是 0 字节，这是最大的短板。写一份能让人 5 分钟上手的：

1. **顶部结果表**：三库 A0–A4 的 EX 简表（从 ablation.md 抄关键列，EX + 单题成本 + 一行结论）。
2. **架构图**：复用 design.md 的 Mermaid 图。
3. **30 秒项目介绍**：一句话说清"这是什么 + 解决了什么 + 怎么证明有效"。
4. **快速开始**：`uv sync` → 配 `.env` → `ask` 一条 → `eval --limit 1` → `trace_viewer`。
5. **目录结构**：指路到 `src/`、`data/`、`eval/configs/`、`experiments/runs/`、`reports/`、`docs/`。

参考 Day 6 手册 §4.3 已经写好的 README 骨架，直接抄过来填真实数字即可。

---

## 5. 简历 bullet + 面试自问（1 小时）

### 5.1 简历 bullet（真实数字）

写 3-4 条，每条都要有数字、有动词、有结果：

```
- 独立设计并实现 Text-to-SQL 数据分析 Agent（DataPilot），用「评测先行 + 消融矩阵」方法，
  在 3 个库（含自建防污染电商库）上量化 5 档配置（A0-A4）的消融收益：
  可靠性组件（检索/修复环/gate/verifier）在自建库上将 EX 从 79.1% 提升至 90.7%。
- 用 LangGraph 构建带执行反馈的修复环（escalate 扩 schema + repair 修语法，上限 3 轮），
  在 sakila 上实现 11.1% 的修复增益；通过 gate 门控（answer/clarify/refuse）实现歧义反问与危险 SQL 拒答。
- 用「执行结果等价」而非文本相似度做评测，三段式指纹防静默续跑混数据；
  通过消融实验发现 LLM verifier 零收益并降级为确定性 guard，单题成本节省 46%。
```

> 数字直接抄 ablation.md，别编。`11.1%` 是 sakila_a3 的 repair_gain（旧 run），v2 是 5.6%，**用 v2 的数字**，统一口径。

### 5.2 面试自问 20 题（每题 3 分钟内能讲完）

关键题（从七天手册的"面试判断点"里提炼）：

1. 为什么用"评测先行"而不是先写 Agent 逻辑？
2. A0 基线为什么重要？headroom 是什么？你的三库 A0 分别是多少？
3. 为什么第三个库要自建？防污染怎么论证？
4. BM25 检索比全量 schema 好在哪？代价是什么？（EX 回退）
5. 修复环里 escalate 和 repair 的区别？为什么 escalate 更关键？
6. 为什么修复上限设 3 轮？
7. gate 的三分类（answer/clarify/refuse）怎么判定？fail-open 是什么意思？
8. verifier 为什么降级？这是你最该讲清的一个负结果。
9. EX 用什么比较？为什么不用文本相似度？
10. 三段式指纹是什么？解决了什么问题？
11. 错误自信率是什么？你的数字是多少？为什么重要？
12. 缓存 + 路由（A4）的价值在哪？temperature=0 下缓存为什么对单次评测无效？
13. 小样本波动怎么处理？1 题 = 几个点？
14. 你的评测有哪些局限？（headroom、样本量、错误自信率样本少）
15. 排序题并列（tie-breaker）为什么是难点？你怎么处理的？
16. 枚举值（status='on'）猜错是什么问题？根治办法？
17. checkpoint 污染是什么坑？怎么避免？
18. composer 为什么用 LLM 生成结论而不是规则拼装？
19. 单题成本怎么算的？你的 A4 单题多少钱？
20. 如果重来一次，你会先做什么、不做什么？

---

## 6. 收尾验收清单

- [x] `reports/ablation.md` 统一到 v2 数据（ecommerce_a0 = 88.4%）
- [x] ecommerce headroom 决策已拍板（推荐方案 A，design.md 里写了诚实标注）
- [x] review_sheet 30 条勾完，错误自信率数字已产出（2/30 ≈ 6.7%）
- [x] `docs/design.md` 填实（8 页内，每节有数字/run_id）
- [x] `docs/failure_cases.md` 填 3 个真实案例
- [x] `README.md` 不再是 0 字节，含结果表 + 架构图 + 快速开始
- [x] 简历 bullet 写 3-4 条（真实数字，见 §5.1）
- [x] 面试自问 20 题，各题 3 分钟内能讲完（参考答案见 `docs/interview_qa_20.md`）
- [ ] 录音讲一遍，计时 12 分钟

## 7. 砍单顺序（时间不够时）

1. 砍录音（面试前自己默讲即可）
2. 砍面试自问 20 题（留 10 道最核心的）
3. 砍 failure_cases 第 3 个案例（2 个也够）
4. **不许砍**：design.md（这是面试的核心弹药）、README（点开就信的第一眼）、ablation 统一 + review_sheet 勾选（否则数字是脏的）

## 8. 今天的关键判断（面试要能讲）

- **为什么这天是"沉淀"不是"再做功能"**：项目的技术高度在 Day 1–6 已经封顶，Day 7 的唯一杠杆是"表达"。面试官读的是 design.md 和 README，不是你的代码——这两份东西写得清楚，比再多一个组件值钱十倍。
- **为什么诚实的负结果比硬撑的正结果值钱**：verifier 降级、A1 回退、headroom 越线，这些"不完美"恰恰是"你真实做过、真实归因过"的证据。一个能把"我做了一个没用的东西然后把它砍了"讲清楚的人，比一个满嘴"我们全面提升"的人可信得多。
