from pathlib import Path

from datapilot.config import settings
from datapilot.nodes.schema_retriever import SchemaRetriever, tokenize

DB = Path(settings.db_dir) / "chinook.db"


def test_tokenize_mixed():
    toks = tokenize("查询 GenreId 对应的流派")
    assert "genreid" in toks and "流派" in toks


def test_direct_hit():
    r = SchemaRetriever(DB)
    got = r.retrieve("客户 Nancy 的邮箱是什么？")
    assert "Customer" in got


def test_fk_expansion_brings_join_table():
    r = SchemaRetriever(DB)
    # "播放列表里有某曲目"命中 Playlist/Track，一跳应补进 PlaylistTrack
    got = r.retrieve("播放列表 Music 里有哪些曲目？")
    assert "PlaylistTrack" in got


def test_determinism():
    r = SchemaRetriever(DB)
    assert r.retrieve("每个国家的客户数") == r.retrieve("每个国家的客户数")