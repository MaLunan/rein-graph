"""G1 顺序引擎测试:A→B→END 流水线、数据流转、到 END、熔断。全程 MockProvider。"""

import asyncio

from rein import Agent, MockProvider

from reingraph.config import GraphConfig
from reingraph.graph import StateGraph
from reingraph.session import GraphSession


def _app():
    """A(Agent,写 output)→ B(Function,读 output 写 final)→ END。"""
    g = StateGraph()
    g.add_node("A", Agent(provider=MockProvider(["from-A"])))

    async def b(sv):
        return {"final": f"got:{sv['output']}"}

    g.add_node("B", b)
    g.set_entry_point("A")
    g.add_edge("A", "B")
    g.set_finish_point("B")
    return g.compile()


def test_顺序流水线数据流转():
    r = _app().invoke({"input": "start"})
    assert r.status == "done"
    assert r.values["output"] == "from-A"  # A 写的
    assert r.values["final"] == "got:from-A"  # B 读到 A 的输出 → 数据真流转


def test_到END后停止():
    r = _app().invoke({"input": "x"})
    assert r.stop_reason == "done"
    assert r.session.done is True


def test_steps按顺序记录每个节点():
    r = _app().invoke({"input": "x"})
    assert [s.node for s in r.steps] == ["A", "B"]


def test_async_ainvoke():
    r = asyncio.run(_app().ainvoke({"input": "x"}))
    assert r.status == "done"


def test_session序列化往返():
    r = _app().invoke({"input": "x"})
    back = GraphSession.model_validate_json(r.session.model_dump_json())
    assert back.state.values["final"] == "got:from-A"


def test_熔断超步上限():
    g = StateGraph()
    g.add_node("A", Agent(provider=MockProvider(["a"])))
    g.add_node("B", Agent(provider=MockProvider(["b"])))
    g.set_entry_point("A")
    g.add_edge("A", "B")
    g.set_finish_point("B")
    r = g.compile(config=GraphConfig(max_supersteps=1)).invoke({"input": "x"})
    assert r.stop_reason == "max_supersteps"  # 第二步前触顶,B 没跑
