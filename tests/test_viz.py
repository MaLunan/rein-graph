"""G7 可视化测试:to_mermaid 文本断言。"""

from rein import Agent, MockProvider

from reingraph.edges import END
from reingraph.graph import StateGraph


def test_顺序图mermaid():
    g = StateGraph()
    g.add_node("A", Agent(provider=MockProvider(["x"])))

    async def b(sv):
        return {}

    g.add_node("B", b)
    g.set_entry_point("A")
    g.add_edge("A", "B")
    g.set_finish_point("B")
    m = g.compile().to_mermaid()
    assert "graph TD" in m
    assert "START --> A" in m
    assert "A --> B" in m
    assert "B --> END" in m


def test_条件边path_map画虚线():
    g = StateGraph()

    async def r(sv):
        return {}

    async def a(sv):
        return {}

    async def b(sv):
        return {}

    g.add_node("r", r)
    g.add_node("a", a)
    g.add_node("b", b)
    g.set_entry_point("r")
    g.add_conditional_edges("r", lambda sv: "a", path_map={"yes": "a", "no": "b"})
    g.add_edge("a", END)
    g.add_edge("b", END)
    m = g.compile().to_mermaid()
    assert "-." in m  # 条件边虚线
    assert "yes" in m and "no" in m  # path_map 分支标签
