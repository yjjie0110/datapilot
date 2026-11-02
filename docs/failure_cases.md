# 失败案例分析

> 三个案例，全部是本项目真实踩过的坑。每个讲清"现象 → 定位 → 根因 → 修复 → 对指标的影响"。

## 案例 1：A4 全 error —— 缓存目录不存在

- **现象**：Day 6 冒烟测试 `eval --config a4 --limit 6`，6 题全部 `status=error`，但同样 6 题用 `--config a3` 全部 `status=ok`。
- **定位过程**：先怀疑是环境变了（langgraph 版本、checkpoint 包缺失），排查一圈发现 A3/A4 走同一个 `graph.py`、import 同一个 `SqliteSaver`，如果 import 有问题 A3 也会挂。于是把差异锁定在 A4 独有的两行配置：`cache: true` 和 `route_small: true`。逐条排查，`route_small` 无问题，问题出在 `cache: true` 触发的 `LLMCache` 初始化。
- **根因**：`LLMCache.__init__` 直接 `sqlite3.connect("experiments/cache/llm_cache.db")`，但父目录 `experiments/cache/` **不存在**，SQLite 无法创建数据库文件 → `sqlite3.OperationalError: unable to open database file`。这个异常在 `build_graph` 阶段就抛出（不在 try 块内），一路冒泡到 runner 的 `score_one` 被捕获成 `status="error"`。A3 不碰缓存所以没事。
- **修复**：连接前 `Path(path).parent.mkdir(parents=True, exist_ok=True)`。
- **对指标的影响**：修复前 A4 全 error（0 分），修复后 A4 正常跑通（三库 EX 落在 66.7%~86.0%）。**这个 bug 让 A4 的消融数据一度完全作废**，必须重跑。
- **面试可引申的点**：相对路径 + 隐式依赖目录是 Python 项目的高频坑；连接外部资源前先确保资源/目录存在，是"防御式初始化"的基本功。

## 案例 2：composer 漏传列名 → 结论空洞

- **现象**：`ask "每个国家客户总消费额前 5 名"`，结论输出"各国客户总消费额前5名共48行，当前展示前10行"或"消费额介于 37.62 至 42.62"——空洞，没点名任何国家/客户。
- **定位过程**：先怀疑"没走 LLM"（结论生成没接上）。查 `llm_calls=4`（比预期多 1 次，正是 compose 那次），说明 LLM 调用确实触发了。再查 composer 的输入，发现问题在 `sample` 的构造。
- **根因**：`sample = "\n".join(str(tuple(r)) for r in rows[:10])` 拼的是**裸元组**（`('Argentina', 1, 'Leone Köhler', 37.62, 1)`），而 `state["columns"]` 没传进 `COMPOSE_USER`。模型面对一堆无列名的元组，不知道 `37.62` 是"消费额"、`Argentina` 是"国家"，只能瞎算一个"介于 X 至 Y"的范围，产出无意义结论。
- **修复**：`sample` 改为带表头（`header + body`），`COMPOSE_USER` 加 `{columns}` 占位符，并要求"点名关键实体和数值"。
- **对指标的影响**：修复后结论变成"仅展示前10行：奥地利 Astrid Gruber 42.62、巴西 Luís Gonçalves 39.62 等"——真正回答问题。同时让"错误自信率"抽评第一次有了可判断的结论文本（此前 composer 输出的是结果 dump，无法判断"过度断言"）。
- **面试可引申的点**：给 LLM 的输入要**显式化语义**——模型会在正确结构上产出错误语义，因为你看似"喂了数据"，其实漏了"数据的含义"（列名）。

## 案例 3：RANK 并列溢出 → SQL 错 + 结论病句

- **现象**：`ask "每个国家客户总消费额前 5 名"`，SQL 用了 `RANK()`，导致"前 5 名"实际多于 5 人（Brazil 第 2 名有 4 人并列 37.62，总行数 48→53，Canada 8 人、USA 7 人溢出）；结论出现病句"巴西第2名均为37.62"。
- **定位过程**：先核结论里"37.62"是否真实（查库确实存在并列），再核 SQL 的窗口函数——发现模型把上一版正确的 `ROW_NUMBER()` 换成了 `RANK()`。
- **根因**：题目"前 N 名"没有写死并列口径，模型在 `RANK()` / `ROW_NUMBER()` / `DENSE_RANK()` 间摇摆，没吃准"前 N 名"的语义（应取恰好 N 人，还是前 N 个名次）。
- **修复**：在 `a0.py` 的 `SYSTEM` 加"排名口径"硬规则——"前 N 名默认用 `ROW_NUMBER()` 取恰好 N 行，禁用 `RANK()`/`DENSE_RANK()`，排名窗口必须带稳定 tie-breaker"。
- **对指标的影响**：改后实测 SQL 用回 `ROW_NUMBER()`、结论无病句。这是**根治**（同时覆盖 A0~A4 所有 generate），而非逐题补丁。但更深层的影响是：它暴露了"排序并列口径"是 Text-to-SQL 的**系统性难点**，在 Day 5 的评测题（ec-011/016/017）已经反复出现，说明这必须靠 prompt 硬规则压制，而非寄望模型自己判断。
- **面试可引申的点**：窗口函数的并列语义（RANK 跳号 / DENSE_RANK 挤名次 / ROW_NUMBER 保 N 行）是 SQL 生成的高频失分点；"语义约束显式化进 prompt"比"遇到一题打一个补丁"更可持续。
