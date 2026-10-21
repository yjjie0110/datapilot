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


# 得到其写system prompt 的规则：
# 如：1. 只允许使用下面 schema 中出现的表和列，禁止臆造表名或列名。
def full_schema_text(db_path: str | Path) -> str:
    """导出完整 schema"""
    conn = connect_ro(db_path)
    lines: list[str] = []
    # 从系统表 sqlite_master 里查表名
    tables = [
        r[0]
        for r in conn.execute(
            "select name from sqlite_master "
            "where type='table' and name not like 'sqlite_%' order by name"
        )
    ]
    for t in tables:
        # 查这张表有多少行，写进标题，例如 TABLE Track (rows=3503)
        n = conn.execute(f'select count(*) from "{t}"').fetchone()[0]
        lines.append(f"TABLE {t}  (rows={n})")

        # PRAGMA table_info(表) 返回该表的每一列（列名、类型、是否主键等）
        for c in conn.execute(f'PRAGMA table_info("{t}")'):
            # 每列格式化成一行：- 列名 类型[ PRIMARY KEY]。例如：  - TrackId INTEGER PRIMARY KEY - Name NVARCHAR(200)
            pk = " PRIMARY KEY" if c["pk"] else ""
            lines.append(f"  - {c['name']} {c['type']}{pk}")

        # PRAGMA foreign_key_list(表) 返回该表的所有外键
        for fk in conn.execute(f'PRAGMA foreign_key_list("{t}")'):
            # 每行输出成 FK: 本表列 -> 目标表.目标列。例如：  FK: AlbumId -> Album.AlbumId
            lines.append(f"  FK: {fk['from']} -> {fk['table']}.{fk['to']}")
        lines.append("")
    conn.close()
    return "\n".join(lines)

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
    #
    # TABLE Track  (rows=3503)
    #   - TrackId INTEGER PRIMARY KEY
    #   - Name NVARCHAR(200)
    #   - AlbumId INTEGER
    #   - MediaTypeId INTEGER
    #   - GenreId INTEGER
    #   - Composer NVARCHAR(220)
    #   - Milliseconds INTEGER
    #   - Bytes INTEGER
    #   - UnitPrice NUMERIC(10,2)
    #   FK: AlbumId -> Album.AlbumId
    #   FK: GenreId -> Genre.GenreId
    #   FK: MediaTypeId -> MediaType.MediaTypeId
    #   ...

if __name__ == "__main__":
    from datapilot.config import settings
    print(settings.db_dir)
    print(full_schema_text(settings.db_dir / "chinook.db"))