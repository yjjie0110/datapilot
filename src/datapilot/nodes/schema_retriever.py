# schema 检索器：BM25 打分 + 外键图一跳扩展。
# 确定性设计：同问题、同库，输出必须完全一致（评测可复现的纪律）。
# 一句话总结：就是对输入的问题，通过bm25 对其存在bm25 中的数据库有关的表进行打分，取前top 个表以及其外键约束的表。
#           使用tokenize() 对数据库进行切分再装入bm25 中，对问题也进行tokenize()划分后再从数据库中找score 最高的表

from __future__ import annotations

import re
from pathlib import Path

from rank_bm25 import BM25Okapi

from datapilot.tools.schema import table_units
from datapilot.tools.sql_runner import sample_rows


def tokenize(text: str) -> list[str]:
    """英文标识符（含驼峰/下划线二次切分）+ 中文单字与二元组。"""
    text = text.lower()  # 将文本转为小写

    toks: list[str] = []
    # 用正则抓「标识符式」单词：以字母或下划线开头，后接字母/数字/下划线。例如 user_id、orderdate，去掉空格等
    for word in re.findall(r"[a-z_][a-z0-9_]*", text):
        toks.append(word)
        # 先保留原词整体（user_id 作为一个 token）。
        # 再按 [a-z]+ 拆出子串：user_id → user、id。这样既保留整体又支持部分匹配。
        toks.extend(re.findall(r"[a-z]+", word))  # 拆下划线

    # 驼峰切分要在小写化之前做，这里退而求其次：原词已入库，靠中文二元组兜底
    # 若test为"中文吗？我试试"，则zh = ['中', '文', '吗', '我', '试', '试']
    zh = re.findall(r"[一-鿿]", text)  # [一-鿿] 是 CJK 统一汉字基本区（U+4E00–U+9FFF），抓出所有中文字符
    toks.extend(zh)
    # 得到toks = ['中', '文', '吗', '我', '试', '试', '中文', '文吗', '吗我', '我试', '试试']
    toks.extend("".join(p) for p in zip(zh, zh[1:]))
    return toks


class SchemaRetriever:
    def __init__(self, db_path: str | Path, sample_n: int = 3):
        self.db_path = Path(db_path)
        # 把 schema 拆成表级单元，每张表一个 dict——检索器的打分对象。
        self.units = table_units(self.db_path)

        self.docs: list[str] = []
        # 为每张表构造一个「检索文档」
        for u in self.units:
            # 把列名拼成一段文本
            col_names = " ".join(c["name"] for c in u["columns"])
            # 把外键信息拼成文本：from 列 指向表 to 列。这样外键关系（尤其是关联表名）也进入检索语料
            fk_text = " ".join(f"{fk['from']} {fk['table']} {fk['to']}" for fk in u["fks"])
            # 取样本行，把每一行每个值 str() 后拼接。这是让「值级线索」参与检索的关键（比如问题里出现 Nancy，能匹配到含 Nancy 的表）
            samples = sample_rows(self.db_path, u["table"], n=sample_n)
            sample_text = " ".join(str(v) for row in samples for v in row)
            # 最终文档 = 表名 + 列名 + 外键文本 + 样本值文本。一张表一段
            self.docs.append(f"{u['table']} {col_names} {fk_text} {sample_text}")

        # 对每个文档分词，构造 BM25 索引。构造时会计算词频、文档频率、IDF、平均文档长度等
        self.bm25 = BM25Okapi([tokenize(d) for d in self.docs])

        # 外键邻接表（双向）
        # 初始化每张表的邻居集合
        self.neighbors: dict[str, set[str]] = {u["table"]: set() for u in self.units}
        for u in self.units:
            for fk in u["fks"]:
                self.neighbors[u["table"]].add(fk["table"])  # 遍历外键：u.table → fk.table 加一条有向边
                if fk["table"] in self.neighbors:
                    self.neighbors[fk["table"]].add(u["table"])  # 再加反向边，构成无向图（双向邻接）

    def retrieve(self, question: str, top_k: int = 4, expand_fk: bool = True) -> list[str]:
        """
            返回表名列表，排序确定（分数降序，平分按表名字典序）。
            args: 问题、BM25 初筛数量、是否做外键扩展
        """
        # 对问题分词，用 BM25 计算每个文档的分数。返回与 self.docs 等长的分数序列
        scores = self.bm25.get_scores(tokenize(question))

        # zip 把「表名」和「分数」配对（units 与 docs 顺序一致，所以能对齐）。
        # 排序键 (-score, table)：
        #   第一关键字 -score：分数高的在前。
        #   第二关键字 table：同分按表名字典序——这是确定性的关键，避免同分时顺序不稳定。
        ranked = sorted(
            zip((u["table"] for u in self.units), scores),
            key=lambda x: (-x[1], x[0]),
        )
        # 取前 top_k，只保留分数 > 0 的表（完全没匹配上的不召回）
        hit = {t for t, s in ranked[:top_k] if s > 0}
        if not hit:  # 全零分时保底取 top_k，宁可多给不能漏，因为下游 SQL 生成时多给表比少给表更安全
            hit = {t for t, _ in ranked[:top_k]}
        if expand_fk:  # 若开启外键扩展：对每个命中的表，把它的邻居也加入结果，结果是一个并集集合，去重
            hit = hit | {nb for t in hit for nb in self.neighbors.get(t, ())}
        return sorted(hit)


if __name__ == "__main__":
    from datapilot.config import settings
    r = SchemaRetriever(settings.db_dir / "chinook.db")
    for q in ["每个音乐流派的曲目数量", "客户 Nancy 的邮箱", "哪些影片被租借次数最多"]:
        print(q, "->", r.retrieve(q))
