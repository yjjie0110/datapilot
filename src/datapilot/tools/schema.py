# 定义了两个函数，用来只读地连接 SQLite 数据库，并把它的完整表结构（含行数、字段、主键、外键）导出成一段可读文本。
# 典型用途是给 LLM 提供数据库 schema 作为 prompt 的上下文（Text-to-SQL 场景）。

import sqlite3
from pathlib import Path


def connect_ro(db_path: str | Path) -> sqlite3.Connection:
    """只读连接。Day 1 就建立这个习惯，别等到 Day 2。"""
    # Path(db_path).as_posix()把路径转成 POSIX 风格（/ 分隔）
    # f"file:...?mode=ro" 用 SQLite 的 URI 模式打开，mode=ro 表示只读，写操作会直接报错
    uri = f"file:{Path(db_path).as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)  # 传入 URI 时必须显式加 uri=True，否则整个字符串会被当文件名
    conn.row_factory = sqlite3.Row  # 让每行结果支持按列名访问（如 row["name"]），而不是只按下标 row[0]
    return conn



def table_units(db_path: str | Path) -> list[dict]:
    """把 schema 拆成表级单元，每张表一个 dict——检索器的打分对象。"""
    conn = connect_ro(db_path)
    # 获取该数据库下的所有用户表名称
    # SELECT name FROM sqlite_master 是 SQLite 中一条查询数据库模式（schema）元数据的 SQL 语句（sqlite_master 系统表中查询所有对象名）
    # 过滤掉sqlite_ 系统表
    tables = [
        r[0]
        for r in conn.execute(
            "select name from sqlite_master "
            "where type='table' and name not like 'sqlite_%' order by name"
        )
    ]
    units: list[dict] = []
    for t in tables:
        # .fetchone()：取第一行结果，返回元组，如 (347,)，就是后去该表中有多少行元素
        n = conn.execute(f'select count(*) from "{t}"').fetchone()[0]

        # 获取当前表 t 的列定义信息，整理成字典列表
        # PRAGMA table_info("{t}")：SQLite 的 PRAGMA 命令，返回该表每一列的元数据
        # c.keys() = ['cid'(列序号), 'name'(列名), 'type'(列名), 'notnull'(列名), 'dflt_value'(默认值), 'pk'(是否为主键的一部分)]
        cols = [
            {"name": c["name"], "type": c["type"], "pk": bool(c["pk"])}
            for c in conn.execute(f'PRAGMA table_info("{t}")')
        ]
        # 获取当前表 t 的外键约束列表，整理成字典列表
        fks = [
            {"from": fk["from"], "table": fk["table"], "to": fk["to"]}
            for fk in conn.execute(f'PRAGMA foreign_key_list("{t}")')
        ]
        units.append({"table": t, "rows": n, "columns": cols, "fks": fks})
    conn.close()
    return units


def unit_to_text(u: dict) -> str:
    """把单个表单元渲染成与 Day 1 完全相同的文本格式。"""
    lines = [f"TABLE {u['table']}  (rows={u['rows']})"]
    for c in u["columns"]:
        pk = " PRIMARY KEY" if c["pk"] else ""
        lines.append(f"  - {c['name']} {c['type']}{pk}")
    for fk in u["fks"]:
        lines.append(f"  FK: {fk['from']} -> {fk['table']}.{fk['to']}")
    return "\n".join(lines)


# 得到其写system prompt 的规则：
# 如：1. 只允许使用下面 schema 中出现的表和列，禁止臆造表名或列名。
def full_schema_text(db_path: str | Path) -> str:
    """与 Day 1 逐字节一致：单元文本 + 每表后一个空行，join 后尾部再去掉一个换行。"""
    units = table_units(db_path)
    return "\n".join(unit_to_text(u) + "\n" for u in units).rstrip("\n")


def schema_text_for(db_path: str | Path, table_names: list[str]) -> str:
    """A1 用：只渲染检索命中的表子集。顺序按表名排序，保证输出确定性。"""
    units = {u["table"]: u for u in table_units(db_path)}
    picked = [units[t] for t in sorted(table_names) if t in units]
    return "\n".join(unit_to_text(u) + "\n" for u in picked).rstrip("\n")

    # 输出大致：
    # TABLE Album  (rows=347)
    #   - AlbumId INTEGER PRIMARY KEY
    #   - Title NVARCHAR(160)
    #   - ArtistId INTEGER
    #   FK: ArtistId -> Artist.ArtistId
    #
    # TABLE Artist  (rows=275)
    #   - ArtistId INTEGER PRIMARY KEY
    #   - Name NVARCHAR(120)
    # ......

if __name__ == "__main__":
    from src.datapilot.config import settings
    print(settings.db_dir)
    # print(full_schema_text(settings.db_dir / "chinook.db"))
    print(schema_text_for(settings.db_dir / "sakila.db", ["actor", "city"]))