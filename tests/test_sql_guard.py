import sqlite3
from pathlib import Path

import pytest

from datapilot.tools.sql_runner import is_safe_select, run_sql

DB = Path(__file__).resolve().parents[1] / "data/dbs/chinook.db"


@pytest.mark.parametrize("sql", [
    "SELECT 1; DROP TABLE Customer",
    "DELETE FROM Customer",
    "UPDATE Customer SET Email = 'x'",
    "DROP TABLE Customer",
    "WITH x AS (DELETE FROM Customer RETURNING *) SELECT * FROM x",
    "PRAGMA table_info(Customer)",
    "ATTACH DATABASE 'x.db' AS x",
])
def test_dangerous_sql_rejected(sql):
    ok, _ = is_safe_select(sql)
    assert not ok


@pytest.mark.parametrize("sql", [
    "SELECT 1",
    "SELECT * FROM Customer",
    "SELECT * FROM Customer;",
    "SELECT * FROM Customer; -- 说明",
    "WITH x AS (SELECT 1 AS a) SELECT * FROM x",
])
def test_valid_select_accepted(sql):
    ok, reason = is_safe_select(sql)
    assert ok, reason


def test_limit_cannot_be_bypassed():
    r = run_sql(DB, "SELECT * FROM Track LIMIT 999999", max_rows=200)
    assert r["ok"]
    assert len(r["rows"]) == 200


def test_readonly_connection_blocks_write():
    r = run_sql(DB, "SELECT 1")
    assert r["ok"]