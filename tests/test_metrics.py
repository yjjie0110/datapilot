# 用来验证 datapilot/eval/metrics.py 里 results_equal 和 explain_mismatch 两个函数的判分语义是否符合设计约定。
# 使用pytest -q 测试

from datapilot.eval.metrics import explain_mismatch, results_equal

# ① 最基本：完全相同
def test_identical():
    assert results_equal([[1, "A"]], [[1, "A"]])

# ② 默认行序无关
def test_row_order_ignored_by_default():
    assert results_equal([["A"], ["B"]], [["B"], ["A"]])

# ③ ordered=True 时行序必须一致
def test_row_order_matters_when_ordered():
    assert not results_equal([["A"], ["B"]], [["B"], ["A"]], ordered=True)

# ④ 重复行必须计数
def test_duplicate_rows_are_counted():
    assert not results_equal([["A"], ["A"]], [["A"]])
    assert results_equal([["A"], ["A"]], [["A"], ["A"]])

# ⑤ int 与 float 兼容
def test_int_vs_float_tolerated():
    assert results_equal([[5], [3]], [[5.0], [3.00]])

# ⑥ NULL 特殊处理
def test_null_handling():
    assert results_equal([[None]], [[None]])
    assert not results_equal([[None]], [[""]])

# ⑦ 数值容差：默认 2 位小数
def test_numeric_tolerance_rounds_to_2():
    assert results_equal([[5.001]], [[5.0]])
    assert not results_equal([[5.01]], [[5.0]])

# ⑧ 字符串大小写默认严格
def test_string_case_strict_by_default():
    assert not results_equal([["Brazil"]], [["brazil"]])
    assert results_equal([["Brazil"]], [["brazil"]], casefold=True)

# ⑨ 空白剥离
def test_whitespace_stripped():
    assert results_equal([["  A "]], [["A"]])

# ⑩ 列数不一致
def test_col_count_diff():
    assert not results_equal([["A", 1]], [["A"]])
    assert "col_count_diff" in explain_mismatch([["A", 1]], [["A"]])

# ⑪ 行数不一致
def test_row_count_diff_reported():
    assert "row_count_diff" in explain_mismatch([["A"]], [["A"], ["B"]])