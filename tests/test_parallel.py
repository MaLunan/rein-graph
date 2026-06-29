"""G3 并行测试:扇出/汇合(map-reduce)、汇合屏障(不对称)、并发安全。纯函数节点,不烧 key。"""

import asyncio

from reingraph.graph import StateGraph


def test_对称扇出汇合map_reduce():
    """split 扇出到 w1/w2/w3 并发 → append reducer 汇合 → merge 等三个都完成。"""
    g = StateGraph(channels={"results": "append"})

    async def split(sv):
        return {}

    async def w1(sv):
        return {"results": "r1"}

    async def w2(sv):
        return {"results": "r2"}

    async def w3(sv):
        return {"results": "r3"}

    async def merge(sv):
        return {"final": sorted(sv["results"])}

    g.add_node("split", split)
    g.add_node("w1", w1)
    g.add_node("w2", w2)
    g.add_node("w3", w3)
    g.add_node("merge", merge)
    g.set_entry_point("split")
    for w in ["w1", "w2", "w3"]:
        g.add_edge("split", w)
        g.add_edge(w, "merge")
    g.set_finish_point("merge")
    r = g.compile().invoke({})
    assert sorted(r.values["results"]) == ["r1", "r2", "r3"]
    assert r.values["final"] == ["r1", "r2", "r3"]


def test_不对称汇合屏障():
    """d 入边来自 b 和 e(e 比 b 多一跳)。d 必须等 b 和 e 都完成才跑。"""
    g = StateGraph(channels={"log": "append"})

    async def a(sv):
        return {"log": "a"}

    async def b(sv):
        return {"log": "b"}

    async def c(sv):
        return {"log": "c"}

    async def e(sv):
        return {"log": "e"}

    async def d(sv):
        return {"d_saw": sorted(sv.get("log", []))}

    for n, f in [("a", a), ("b", b), ("c", c), ("e", e), ("d", d)]:
        g.add_node(n, f)
    g.set_entry_point("a")
    g.add_edge("a", "b")
    g.add_edge("a", "c")
    g.add_edge("c", "e")
    g.add_edge("b", "d")
    g.add_edge("e", "d")
    g.set_finish_point("d")
    r = g.compile().invoke({})
    assert "b" in r.values["d_saw"] and "e" in r.values["d_saw"]


def test_并发100次不串台():
    """同一个 CompiledGraph 并发跑 100 个不同输入,每个结果对应自己的输入。"""

    async def echo(sv):
        return {"out": f"echo:{sv['input']}"}

    g = StateGraph()
    g.add_node("n", echo)
    g.set_entry_point("n")
    g.set_finish_point("n")
    app = g.compile()

    async def main():
        return await asyncio.gather(
            *[app.ainvoke({"input": f"req-{i}"}, thread_id=f"t{i}") for i in range(100)]
        )

    rs = asyncio.run(main())
    for i, r in enumerate(rs):
        assert r.values["out"] == f"echo:req-{i}", (i, r.values)
