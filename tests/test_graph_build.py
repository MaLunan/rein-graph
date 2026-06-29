"""G1 构建器测试:add_node 智能适配、@graph.node 糖、编译期校验。"""

import pytest
from rein import Agent, MockProvider

from reingraph.graph import StateGraph
from reingraph.nodes import AgentNode, FunctionNode


def test_add_node_agent自动包AgentNode():
    g = StateGraph()
    g.add_node("a", Agent(provider=MockProvider(["x"])))
    assert isinstance(g._nodes["a"], AgentNode)


def test_add_node_函数自动包FunctionNode():
    g = StateGraph()

    async def f(sv):
        return {}

    g.add_node("f", f)
    assert isinstance(g._nodes["f"], FunctionNode)


def test_node装饰器糖():
    g = StateGraph()

    @g.node("x")
    async def x(sv):
        return {"k": 1}

    assert "x" in g._nodes


def test_编译无入口报错():
    with pytest.raises(ValueError):
        StateGraph().compile()


def test_编译边端点不存在报错():
    g = StateGraph()

    async def f(sv):
        return {}

    g.add_node("a", f)
    g.set_entry_point("a")
    g.add_edge("a", "nonexistent")
    with pytest.raises(ValueError):
        g.compile()


def test_set_finish_point():
    g = StateGraph()
    g.add_node("a", Agent(provider=MockProvider(["x"])))
    g.set_entry_point("a")
    g.set_finish_point("a")
    app = g.compile()
    assert app.entry == "a"
