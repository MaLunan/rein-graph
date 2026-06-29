"""G6 子图测试:CompiledGraph 作节点、输出冒泡、嵌套 HITL(中断冒泡 + 嵌套快照 + resume 分发)。"""

from rein import Agent, LoopConfig, MockProvider, ToolCall

from reingraph.graph import StateGraph
from reingraph.session import GraphSession


def test_子图作节点输出冒泡():
    sub = StateGraph()

    async def inner(sv):
        return {"sub_out": f"p:{sv['input']}"}

    sub.add_node("inner", inner)
    sub.set_entry_point("inner")
    sub.set_finish_point("inner")

    parent = StateGraph()

    async def pre(sv):
        return {"input": "data"}

    parent.add_node("pre", pre)
    parent.add_node("child", sub.compile())  # 子图当节点
    parent.set_entry_point("pre")
    parent.add_edge("pre", "child")
    parent.set_finish_point("child")
    r = parent.compile().invoke({})
    assert r.values["sub_out"] == "p:data"


def _ask_subgraph_app():
    a = Agent(
        provider=MockProvider([[ToolCall(id="1", name="d", arguments={})]]),
        config=LoopConfig(permission="ask"),
    )

    @a.tool
    def d() -> str:
        "d"
        return "x"

    sub = StateGraph()
    sub.add_node("approve", a)
    sub.set_entry_point("approve")
    sub.set_finish_point("approve")
    parent = StateGraph()
    parent.add_node("child", sub.compile())
    parent.set_entry_point("child")
    parent.set_finish_point("child")
    return parent.compile()


def test_嵌套HITL中断冒泡到父():
    r = _ask_subgraph_app().invoke({"input": "go"})
    assert r.status == "interrupted"
    assert r.interrupt.node == "child"
    assert r.interrupt.inner.type == "need_approval"


def test_嵌套快照序列化往返():
    r = _ask_subgraph_app().invoke({"input": "go"})
    back = GraphSession.model_validate_json(r.session.model_dump_json())
    assert "child" in back.sub_sessions  # 子图快照嵌在父快照里


def test_嵌套HITL_resume分发回子图():
    app = _ask_subgraph_app()
    r = app.invoke({"input": "go"})
    rr = app.resume(r.session, approve=True)
    assert rr.status == "done"
