"""G4 checkpoint 测试:GraphSession 序列化往返(含中断态)+ Memory/File store 一致。"""

from rein import Agent, LoopConfig, MockProvider, ToolCall

from reingraph.graph import StateGraph
from reingraph.session import GraphSession
from reingraph.store import FileGraphStore, MemoryGraphStore


def _interrupted_session() -> GraphSession:
    """跑一个会中断的图,拿到中断态的 GraphSession(含 pending_interrupt + node_sessions)。"""
    a = Agent(
        provider=MockProvider([[ToolCall(id="1", name="d", arguments={})]]),
        config=LoopConfig(permission="ask"),
    )

    @a.tool
    def d() -> str:
        "d"
        return "x"

    g = StateGraph()
    g.add_node("step", a)
    g.set_entry_point("step")
    g.set_finish_point("step")
    return g.compile().invoke({"input": "go"}).session


def test_中断态session序列化往返():
    gs = _interrupted_session()
    back = GraphSession.model_validate_json(gs.model_dump_json())
    assert back.pending_interrupt is not None
    assert back.pending_interrupt.node == "step"
    assert "step" in back.node_sessions  # 嵌套的 rein.Session 一并还原


def test_memory_store往返():
    gs = _interrupted_session()
    s = MemoryGraphStore()
    s.save("t", gs)
    back = s.load("t")
    assert back is not None and back.pending_interrupt.node == "step"


def test_file_store往返(tmp_path):
    gs = _interrupted_session()
    s = FileGraphStore(str(tmp_path / "sessions"))
    s.save("t", gs)
    back = s.load("t")
    assert back is not None
    assert back.pending_interrupt.node == "step"
    assert "step" in back.node_sessions


def test_file_store不存在返回None(tmp_path):
    s = FileGraphStore(str(tmp_path / "s2"))
    assert s.load("nope") is None
