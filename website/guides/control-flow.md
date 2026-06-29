# 条件分支与循环

用 `add_conditional_edges` 让图「看状态决定下一步」。

## 条件分支

`routing_fn(state)` 返回下一个节点名:

```python
from reingraph import StateGraph
from reingraph.edges import END

g = StateGraph()
g.add_node("triage", classify_agent)      # 写 state["category"]
g.add_node("refund", refund_agent)
g.add_node("faq", faq_agent)
g.set_entry_point("triage")
g.add_conditional_edges(
    "triage",
    lambda s: "refund" if s["category"] == "退款" else "faq",
    path_map={"refund": "refund", "faq": "faq"},   # 可选,便于可视化
)
g.add_edge("refund", END)
g.add_edge("faq", END)
```

`routing_fn` 可返回:节点名(分支)、节点名列表(扇出,见[并行](parallel.md))、或 `END`。

## 循环(reflexion 式自我反思)

循环 = `routing_fn` 返回**上游节点名**,引擎把它加回 frontier:

```python
g = StateGraph(channels={"round": "add"})
g.add_node("generate", writer_agent)
g.add_node("critique", critic_agent)      # 写 state["ok"]
g.set_entry_point("generate")
g.add_edge("generate", "critique")
g.add_conditional_edges(
    "critique",
    lambda s: END if s.get("ok") or s["round"] >= 3 else "generate",  # 不满意就回去重写
)
```

## 防失控:双闸熔断

循环靠两道闸兜底(照抄 rein 的 `check_circuit` 心法):

```python
from reingraph import GraphConfig

app = g.compile(config=GraphConfig(
    max_node_visits=10,    # 单节点最多进入 10 次
    max_supersteps=100,    # 整图最多 100 个超步
))
```

触顶时图安全停止,`result.stop_reason` 给出 `max_node_visits` / `max_supersteps`。
