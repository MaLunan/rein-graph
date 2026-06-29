"""条件分支 + 循环 —— 两种最常见的控制流。

  1. 条件路由:triage 节点决定走 A 还是 B 分支(`add_conditional_edges` + routing_fn);
  2. reflexion 循环:improve 节点反复自我改进,直到达标才结束(routing_fn 返回 END 收口)。

全程 MockProvider —— 离线、零成本、确定性。运行:python examples/control_flow.py
"""

from rein import Agent, MockProvider

from reingraph import StateGraph
from reingraph.edges import END


def build_router():
    """条件路由:triage → handle_a / handle_b。"""
    g = StateGraph()
    g.add_node("triage", Agent(provider=MockProvider(["A"])))  # 假装把工单分类成 A
    g.add_node("handle_a", Agent(provider=MockProvider(["走了 A 分支"])))
    g.add_node("handle_b", Agent(provider=MockProvider(["走了 B 分支"])))
    g.set_entry_point("triage")
    g.add_conditional_edges(
        "triage",
        lambda s: "handle_a" if "A" in (s.get("output") or "") else "handle_b",
    )
    g.add_edge("handle_a", END)
    g.add_edge("handle_b", END)
    return g.compile()


def build_loop():
    """reflexion 循环:每轮 score +1,< 3 就回到自己,>= 3 收口(routing 返回 END)。"""
    g = StateGraph()

    async def improve(sv):
        return {"score": (sv.get("score") or 0) + 1}

    g.add_node("improve", improve)
    g.set_entry_point("improve")
    g.add_conditional_edges(
        "improve",
        lambda s: END if (s.get("score") or 0) >= 3 else "improve",
    )
    return g.compile()


if __name__ == "__main__":
    r1 = build_router().invoke({"input": "处理这个工单"})
    print("① 条件路由 →", r1.values["output"])

    r2 = build_loop().invoke({"input": "开始"})
    print("② 循环到达标 → score =", r2.values["score"])
