from src.datapilot.nodes.verifier import deterministic_flags, node_verify


def test_flags_all_null_rows():
    assert deterministic_flags([(None, None)], ["a", "b"], False)


def test_flags_null_column():
    flags = deterministic_flags([(1, None), (2, None)], ["id", "x"], False)
    assert any("整列全 NULL" in f for f in flags)


def test_flags_truncated():
    assert deterministic_flags([(1,)], ["a"], True)


def test_flags_clean():
    assert deterministic_flags([(1, "a"), (2, "b")], ["id", "name"], False) == []


class _Resp:
    text = '{"verdict": "wrong", "reason": "SELECT 列与问题不符"}'
    cost_cny = 0.001
    in_tokens = 100


class _FakeClient:
    def chat_json(self, system, user):
        return _Resp()


def test_verify_skips_llm_on_easy_clean():
    out = node_verify({"rows": [(1,)], "columns": ["a"], "truncated": False,
                       "difficulty": 1, "question": "q", "sql": "SELECT 1"},
                      _FakeClient())
    assert out["verify"]["verdict"] == "pass"
    assert "llm_calls" not in out  # 没调 LLM 就不许返回累加字段（否则多计）


def test_verify_calls_llm_on_flags():
    out = node_verify({"rows": [(None,)], "columns": ["a"], "truncated": False,
                       "difficulty": 1, "question": "q", "sql": "SELECT 1"},
                      _FakeClient())
    assert out["verify"]["verdict"] == "wrong"
    assert out["llm_calls"] == 1


def test_verify_fail_open_on_bad_json():
    class _BadClient:
        def chat_json(self, system, user):
            r = _Resp()
            r.text = " garbage "
            return r
    out = node_verify({"rows": [(None,)], "columns": ["a"], "truncated": False,
                       "difficulty": 3, "question": "q", "sql": "SELECT 1"},
                      _BadClient())
    assert out["verify"]["verdict"] == "pass"
