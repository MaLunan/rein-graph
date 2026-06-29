"""G4 图级 HITL 测试:中断冒泡 → 存盘 → resume(批准/拒绝/直接 session)→ 完成。全 MockProvider。"""

import pytest
from rein import Agent, LoopConfig, MockProvider, ToolCall

from reingraph.graph import StateGraph
from reingraph.store import MemoryGraphStore


def _ask_agent():
    a = Agent(
        provider=MockProvider([[ToolCall(id="1", name="danger", arguments={})]]),
        config=LoopConfig(permission="ask"),
    )

    @a.tool
    def danger() -> str:
        "危险操作"
        return "executed"

    return a


def _app(store=None):
    g = StateGraph()
    g.add_node("step", _ask_agent())
    g.set_entry_point("step")
    g.set_finish_point("step")
    return g.compile(store=store)


def test_中断冒泡到图级():
    r = _app().invoke({"input": "do"})
    assert r.status == "interrupted"
    assert r.interrupt.node == "step"
    assert r.interrupt.inner.type == "need_approval"


def test_存盘后从thread_id恢复批准():
    store = MemoryGraphStore()
    app = _app(store)
    app.invoke({"input": "do"}, thread_id="j1")
    r = app.resume("j1", approve=True)
    assert r.status == "done"


def test_拒绝后自愈完成():
    store = MemoryGraphStore()
    app = _app(store)
    app.invoke({"input": "do"}, thread_id="j2")
    r = app.resume("j2", approve=False)
    assert r.status == "done"  # 拒绝 → 错误结果回填 → agent 自愈


def test_直接传session恢复():
    app = _app()
    ri = app.invoke({"input": "do"})
    r = app.resume(ri.session, approve=True)
    assert r.status == "done"


def test_thread_id无store报错():
    app = _app()  # 没配 store
    with pytest.raises(ValueError):
        app.resume("nonexistent", approve=True)
