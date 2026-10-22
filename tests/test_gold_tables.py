from datapilot.eval.gold_tables import extract_tables


def test_simple_join():
    sql = "SELECT * FROM Track t JOIN Genre g ON t.GenreId = g.GenreId"
    assert extract_tables(sql) == ["Genre", "Track"]


def test_cte_alias_excluded():
    sql = "WITH x AS (SELECT GenreId FROM Track) SELECT * FROM x JOIN Genre USING (GenreId)"
    assert extract_tables(sql) == ["Genre", "Track"]  # x 是 CTE 别名，不是表


def test_subquery():
    sql = "SELECT * FROM Customer WHERE CustomerId IN (SELECT CustomerId FROM Invoice)"
    assert extract_tables(sql) == ["Customer", "Invoice"]
