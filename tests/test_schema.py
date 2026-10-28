from pathlib import Path

from src.datapilot.config import settings
from src.datapilot.tools.schema import full_schema_text, schema_text_for, table_units

DB = Path(settings.db_dir) / "chinook.db"

# Day 1 输出的前 80 字符快照——重构后必须一致
def test_full_schema_stable_prefix():
    text = full_schema_text(DB)
    assert text.startswith("TABLE Album  (rows=347)\n  - AlbumId INTEGER PRIMARY KEY")
    assert "FK: ArtistId -> Artist.ArtistId" in text
    assert text.count("TABLE ") == 11


def test_units_cover_all_tables():
    units = table_units(DB)
    assert len(units) == 11
    track = next(u for u in units if u["table"] == "Track")
    assert any(c["name"] == "UnitPrice" for c in track["columns"])
    assert any(fk["table"] == "Album" for fk in track["fks"])


def test_subset_rendering():
    text = schema_text_for(DB, ["Track", "Genre"])
    assert "TABLE Track" in text and "TABLE Genre" in text
    assert "TABLE Album" not in text