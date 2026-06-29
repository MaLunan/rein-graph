"""子图:把一个编译好的图当作另一个图的节点(SubGraphNode)—— 拓扑可分层复用。

外层:prepare → [子图:research → summarize] → finalize。
全程 MockProvider —— 离线可跑。运行:python examples/subgraph.py
"""

from rein import Agent, MockProvider

from reingraph import StateGraph


def build_subgraph():
    g = StateGraph()
    g.add_node("research", Agent(provider=MockProvider(["调研结果"])))
    g.add_node("summarize", Agent(provider=MockProvider(["子图摘要"])))
    g.set_entry_point("research")
    g.add_edge("research", "summarize")
    g.set_finish_point("summarize")
    return g.compile()


def build_main():
    g = StateGraph()
    g.add_node("prepare", Agent(provider=MockProvider(["准备好了"])))
    g.add_node("sub", build_subgraph())  # 子图作为一个节点(add_node 自动识别 CompiledGraph)
    g.add_node("finalize", Agent(provider=MockProvider(["定稿"])))
    g.set_entry_point("prepare")
    g.add_edge("prepare", "sub")
    g.add_edge("sub", "finalize")
    g.set_finish_point("finalize")
    return g.compile()


if __name__ == "__main__":
    r = build_main().invoke({"input": "做个报告"})
    print("子图编排完成 → status =", r.status)
    print("最终 output =", r.values.get("output"))
