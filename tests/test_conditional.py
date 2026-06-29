"""G2 条件分支 + 循环测试。全程纯函数节点,不烧 key。"""

from reingraph.config import GraphConfig
from reingraph.edges import END
from reingraph.graph import StateGraph


def _router_app():
    g = StateGraph()

    async def router(sv):
        return {"route": sv["input"]}

    async def path_a(sv):
        return {"result": "A"}

    async def path_b(sv):
        return {"result": "B"}

    g.add_node("router", router)
    g.add_node("a", path_a)
    g.add_node("b", path_b)
    g.set_entry_point("router")
    g.add_conditional_edges("router", lambda sv: "a" if sv["route"] == "x" else "b")
    g.add_edge("a", END)
    g.add_edge("b", END)
    return g.compile()


def test_条件分支走a():
    assert _router_app().invoke({"input": "x"}).values["result"] == "A"


def test_条件分支走b():
    assert _router_app().invoke({"input": "y"}).values["result"] == "B"


def test_path_map映射():
    g = StateGraph()

    async def r(sv):
        return {}

    async def a(sv):
        return {"v": "A"}

    g.add_node("r", r)
    g.add_node("a", a)
    g.set_entry_point("r")
    g.add_conditional_edges("r", lambda sv: "yes", path_map={"yes": "a"})
    g.add_edge("a", END)
    assert g.compile().invoke({}).values["v"] == "A"


def test_循环自增到条件停():
    g = StateGraph(channels={"n": "add"})

    async def inc(sv):
        return {"n": 1}

    g.add_node("inc", inc)
    g.set_entry_point("inc")
    g.add_conditional_edges("inc", lambda sv: "inc" if sv["n"] < 3 else END)
    r = g.compile().invoke({})
    assert r.values["n"] == 3 and r.status == "done"


def test_循环熔断max_node_visits():
    g = StateGraph()

    async def loop(sv):
        return {}

    g.add_node("loop", loop)
    g.set_entry_point("loop")
    g.add_conditional_edges("loop", lambda sv: "loop")
    r = g.compile(config=GraphConfig(max_node_visits=5)).invoke({})
    assert r.stop_reason == "max_node_visits"


def test_routing返回END直接结束():
    g = StateGraph()

    async def n(sv):
        return {"k": 1}

    g.add_node("n", n)
    g.set_entry_point("n")
    g.add_conditional_edges("n", lambda sv: END)
    assert g.compile().invoke({}).status == "done"
