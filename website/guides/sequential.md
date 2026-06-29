# 顺序流水线

最简单的图:节点依次执行,数据沿边流转。

```python
from reingraph import AgentNode, StateGraph
from rein import Agent

g = StateGraph()
g.add_node("plan", Agent(model="anthropic/claude-opus-4-8", system="列大纲"))
g.add_node(
    "write",
    AgentNode(
        "write",
        Agent(model="anthropic/claude-opus-4-8", system="按大纲成文"),
        input_key="output",     # 读上一步 plan 写的 output
        output_key="article",   # 自己的结果写到 article
    ),
)
g.set_entry_point("plan")
g.add_edge("plan", "write")
g.set_finish_point("write")

r = g.compile().invoke({"input": "写一篇关于缰绳的短文"})
print(r.values["article"])
```

## 节点间怎么传数据

- AgentNode 默认 `input_key="input"`、`output_key="output"`:读 `state["input"]` 当 prompt,把回答写 `state["output"]`。
- 让 B 读 A 的输出:把 B 的 `input_key` 设成 A 的 `output_key`(上例 `write` 读 `output`)。
- 或用 `prompt_fn=lambda state: f"{state['x']}-{state['y']}"` 自定义拼 prompt。
- FunctionNode 直接 `return {"键": 值}` 更新 state。

## 结果对象 GraphResult

`invoke` 返回 `GraphResult`:`.values`(最终状态)、`.status`(done/interrupted)、`.usage`(全图用量)、`.steps`(带节点归属的流水账)、`.stop_reason`。
