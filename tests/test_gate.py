from src.datapilot.nodes.gate import node_gate


class _Resp:
    def __init__(self, text):
        self.text = text
        self.cost_cny = 0.001
        self.in_tokens = 100


class _FakeClient:
    def __init__(self, text):
        self._text = text

    def chat_json(self, system, user):
        return _Resp(self._text)


def _state():
    # db_id 必须给真实库：方案 A 后 gate 会读全库表清单（_full_catalog）。
    # 这里走真实 chinook 反而更好——顺带覆盖了目录加载路径。
    return {"question": "q", "db_id": "chinook", "schema_text": "CREATE TABLE T(id INT);"}


def test_gate_fail_open_on_bad_json():
    out = node_gate(_state(), _FakeClient("这不是JSON"))
    assert out["gate"]["action"] == "answer"
    assert "behavior" not in out  # 放行时不许动 behavior


def test_gate_fail_open_on_unknown_action():
    out = node_gate(_state(), _FakeClient('{"action": "maybe", "reason": "x"}'))
    assert out["gate"]["action"] == "answer"


def test_gate_clarify_sets_behavior():
    out = node_gate(_state(), _FakeClient(
        '{"action": "clarify", "reason": "口径未定义", "clarifying_question": "按销量还是评分？"}'))
    assert out["behavior"] == "clarify"
    assert out["gate"]["clarifying_question"] == "按销量还是评分？"


def test_gate_refuse_sets_behavior():
    out = node_gate(_state(), _FakeClient(
        '{"action": "refuse", "reason": "库中无该列", "clarifying_question": ""}'))
    assert out["behavior"] == "refuse"
