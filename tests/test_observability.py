"""G5 可观测测试:usage 聚合(各节点之和)、steps 带节点归属。"""

from rein import Agent, MockProvider

from reingraph.graph import StateGraph


def _two_agent_app():
    g = StateGraph()
    g.add_node("X", Agent(provider=MockProvider(["x"])))
    g.add_node("Y", Agent(provider=MockProvider(["y"])))
    g.set_entry_point("X")
    g.add_edge("X", "Y")
    g.set_finish_point("Y")
    return g.compile()


def test_usage聚合各节点之和():
    r = _two_agent_app().invoke({"input": "q"})
    assert r.usage.input_tokens >= 2  # 两个 agent 的用量累加
    assert r.usage.output_tokens >= 2


def test_steps带节点归属():
    r = _two_agent_app().invoke({"input": "q"})
    assert [s.node for s in r.steps] == ["X", "Y"]
    assert all(s.kind == "node" for s in r.steps)
