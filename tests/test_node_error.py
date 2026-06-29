"""节点异常处理:节点抛异常 → 错误中断(不炸整图、进度保留)→ resume 重试 / 放弃。"""

from reingraph.graph import StateGraph
from reingraph.session import GraphSession


def test_节点异常转错误中断():
    async def boom(sv):
        raise ValueError("炸")

    g = StateGraph()
    g.add_node("b", boom)
    g.set_entry_point("b")
    g.set_finish_point("b")
    r = g.compile().invoke({"input": "x"})
    assert r.status == "interrupted"
    assert r.interrupt.inner.type == "error"
    assert "炸" in r.interrupt.inner.message


def test_resume重试成功():
    calls = {"n": 0}

    async def flaky(sv):
        calls["n"] += 1
        if calls["n"] == 1:
            raise ValueError("第一次失败")
        return {"out": "ok"}

    g = StateGraph()
    g.add_node("flaky", flaky)
    g.set_entry_point("flaky")
    g.set_finish_point("flaky")
    app = g.compile()
    r = app.invoke({"input": "go"})
    assert r.status == "interrupted"
    r2 = app.resume(r.session, approve=True)
    assert r2.status == "done" and r2.values["out"] == "ok"


def test_并行成功节点进度保留():
    async def boom(sv):
        raise RuntimeError("炸")

    async def good(sv):
        return {"good_ran": True}

    async def split(sv):
        return {}

    g = StateGraph()
    for n, f in [("split", split), ("boom", boom), ("good", good)]:
        g.add_node(n, f)
    g.set_entry_point("split")
    g.add_edge("split", "boom")
    g.add_edge("split", "good")
    r = g.compile().invoke({"input": "x"})
    assert r.status == "interrupted"
    assert r.values.get("good_ran") is True  # 异常节点不影响成功兄弟的进度


def test_放弃停止():
    async def boom(sv):
        raise ValueError("炸")

    g = StateGraph()
    g.add_node("b", boom)
    g.set_entry_point("b")
    g.set_finish_point("b")
    app = g.compile()
    r = app.invoke({"input": "x"})
    r2 = app.resume(r.session, approve=False)
    assert r2.stop_reason == "node_error_abandoned"


def test_错误态可序列化往返():
    async def boom(sv):
        raise ValueError("炸")

    g = StateGraph()
    g.add_node("b", boom)
    g.set_entry_point("b")
    g.set_finish_point("b")
    r = g.compile().invoke({"input": "x"})
    back = GraphSession.model_validate_json(r.session.model_dump_json())
    assert back.pending_interrupt.inner.type == "error"


def test_重试又失败再次错误中断():
    async def always(sv):
        raise ValueError("总是炸")

    g = StateGraph()
    g.add_node("b", always)
    g.set_entry_point("b")
    g.set_finish_point("b")
    app = g.compile()
    r = app.invoke({"input": "x"})
    r2 = app.resume(r.session, approve=True)  # 重试又炸
    assert r2.status == "interrupted" and r2.interrupt.inner.type == "error"
