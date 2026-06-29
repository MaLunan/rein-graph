"""state.py 测试:reducer 行为 + apply_updates 合并 + GraphState 序列化往返。"""

from reingraph.state import GraphState, apply_updates, make_state, register_reducer


def test_last_write_wins默认覆盖():
    s = apply_updates(GraphState(), {"x": 1})
    s = apply_updates(s, {"x": 2})
    assert s.values["x"] == 2


def test_append汇合():
    s = make_state({"notes": "append"})
    s = apply_updates(s, {"notes": "a"})
    s = apply_updates(s, {"notes": "b"})
    assert s.values["notes"] == ["a", "b"]


def test_append接受列表():
    s = make_state({"items": "append"})
    s = apply_updates(s, {"items": [1, 2]})
    s = apply_updates(s, {"items": 3})
    assert s.values["items"] == [1, 2, 3]


def test_add累加():
    s = make_state({"score": "add"})
    s = apply_updates(s, {"score": 5})
    s = apply_updates(s, {"score": 3})
    assert s.values["score"] == 8


def test_merge_dict合并():
    s = make_state({"meta": "merge_dict"})
    s = apply_updates(s, {"meta": {"a": 1}})
    s = apply_updates(s, {"meta": {"b": 2}})
    assert s.values["meta"] == {"a": 1, "b": 2}


def test_未声明键补默认声明():
    s = apply_updates(GraphState(), {"new": "z"})
    assert s.values["new"] == "z"
    assert "new" in s.channels


def test_序列化往返():
    s = make_state({"notes": "append", "score": "add"}, {"x": 1})
    s = apply_updates(s, {"notes": "a", "score": 5})
    r = GraphState.model_validate_json(s.model_dump_json())
    assert r.values == s.values
    assert r.channels["notes"].reducer == "append"


def test_自定义reducer注册():
    register_reducer("max_r", lambda old, new: max(old or 0, new))
    s = make_state({"hi": "max_r"})
    s = apply_updates(s, {"hi": 3})
    s = apply_updates(s, {"hi": 1})
    assert s.values["hi"] == 3


def test_apply_updates不原地改():
    s0 = make_state(initial={"x": 1})
    s1 = apply_updates(s0, {"x": 2})
    assert s0.values["x"] == 1  # 原对象不变(纯函数)
    assert s1.values["x"] == 2
