"""G5 流式测试:astream 事件序列、done 带最终状态、中断发 interrupt 事件。"""

import asyncio

from rein import Agent, LoopConfig, MockProvider, ToolCall

from reingraph.graph import StateGraph


def _collect(app, inputs):
    async def main():
        return [ev async for ev in app.astream(inputs)]

    return asyncio.run(main())


def test_流式事件序列():
    g = StateGraph()
    g.add_node("A", Agent(provider=MockProvider(["a"])))

    async def b(sv):
        return {"final": "b"}

    g.add_node("B", b)
    g.set_entry_point("A")
    g.add_edge("A", "B")
    g.set_finish_point("B")
    types = [e.type for e in _collect(g.compile(), {"input": "x"})]
    assert types[0] == "superstep_start"
    assert "node_start" in types and "node_end" in types and "state_update" in types
    assert types[-1] == "done"


def test_done事件带最终状态():
    g = StateGraph()

    async def n(sv):
        return {"out": "done-val"}

    g.add_node("n", n)
    g.set_entry_point("n")
    g.set_finish_point("n")
    evs = _collect(g.compile(), {})
    assert evs[-1].type == "done"
    assert evs[-1].values["out"] == "done-val"


def test_中断发interrupt事件并停止():
    a = Agent(
        provider=MockProvider([[ToolCall(id="1", name="d", arguments={})]]),
        config=LoopConfig(permission="ask"),
    )

    @a.tool
    def d() -> str:
        "d"
        return "x"

    g = StateGraph()
    g.add_node("s", a)
    g.set_entry_point("s")
    g.set_finish_point("s")
    types = [e.type for e in _collect(g.compile(), {"input": "go"})]
    assert "interrupt" in types
    assert types[-1] == "interrupt"  # 中断后流停止
