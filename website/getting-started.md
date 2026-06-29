# 快速开始

## 安装

```bash
pip install rein-graph        # 会自动带上 rein-agent
```

```python
import reingraph
from rein import Agent
```

reinGraph 依赖 `rein-agent`(装完即接入真实大模型,经 LiteLLM)。

## 第一个图:顺序流水线

```python
from reingraph import StateGraph
from rein import Agent

g = StateGraph()
g.add_node("plan", Agent(model="anthropic/claude-opus-4-8", system="先列大纲"))
g.add_node("write", Agent(model="anthropic/claude-opus-4-8", system="按大纲成文"))
g.set_entry_point("plan")
g.add_edge("plan", "write")
g.set_finish_point("write")

app = g.compile()
result = app.invoke({"input": "写一篇关于缰绳的短文"})
print(result.values["output"])
```

- `add_node` 传一个 `rein.Agent` → 自动包成图节点;
- `add_edge("plan", "write")` 连成流水线;
- `invoke` 从入口跑到 `END`,返回 `GraphResult`(`.values` / `.status` / `.usage` / `.steps`)。

## 不联网先跑通(MockProvider)

不想烧 key,可用 rein 自带的 `MockProvider` 离线跑通整个编排:

```python
from reingraph import StateGraph
from rein import Agent, MockProvider

g = StateGraph()
g.add_node("a", Agent(provider=MockProvider(["第一步结果"])))

async def b(state):                       # 普通 async 函数也能当节点
    return {"final": f"加工:{state['output']}"}

g.add_node("b", b)
g.set_entry_point("a")
g.add_edge("a", "b")
g.set_finish_point("b")

r = g.compile().invoke({"input": "开始"})
print(r.values["final"])     # 加工:第一步结果
```

## 三种节点

| 节点 | 怎么来 | 干什么 |
|---|---|---|
| **AgentNode** | `add_node(name, Agent(...))` | 跑一个 rein agent(读 state 取 prompt,写 output) |
| **FunctionNode** | `add_node(name, async_fn)` 或 `@graph.node` | 普通函数做编排粘合(取数 / 转换) |
| **SubGraphNode** | `add_node(name, 另一个 compiled_graph)` | 把子图当节点(嵌套复用) |

## 下一步

- [核心概念](concepts.md):状态(channel/reducer)、边、超步引擎、HITL。
- [指南](guides/sequential.md):顺序 / 条件循环 / 并行 / HITL / 子图 / 可视化。
- [设计哲学](design.md):reinGraph 如何复用 rein 而非重造。
