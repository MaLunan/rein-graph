# 并行扇出与汇合(map-reduce)

一个节点扇出到多个 agent **并发**跑,再用 reducer **汇合**结果。

```python
from reingraph import AgentNode, StateGraph
from rein import Agent

# drafts 用 append reducer —— 三个分支各 append 自己的产出
g = StateGraph(channels={"drafts": "append"})

async def split(state):
    return {}

g.add_node("split", split)
for i, persona in enumerate(["乐观", "谨慎", "创新"]):
    g.add_node(
        f"w{i}",
        AgentNode(f"w{i}", Agent(model="anthropic/claude-opus-4-8", system=f"{persona}视角"),
                  output_key="drafts"),
    )

async def merge(state):
    return {"final": "\n---\n".join(state["drafts"])}

g.add_node("merge", merge)
g.set_entry_point("split")
for i in range(3):
    g.add_edge("split", f"w{i}")   # 扇出:split → w0/w1/w2
    g.add_edge(f"w{i}", "merge")   # 汇合:w0/w1/w2 → merge
g.set_finish_point("merge")

r = g.compile().invoke({"input": "评估这个方案"})
print(r.values["final"])
```

## 工作原理

- **扇出**:`split` 有三条出边 → 下一超步 frontier = `[w0, w1, w2]`,引擎用 `asyncio.gather` 并发跑。
- **汇合**:三个 worker 都写 `drafts` 键,`append` reducer 把它们并成一个列表(顺序固定、可复现)。
- **汇合屏障**:`merge` 的三个上游都完成后才跑(不会在某个 worker 没好时提前抢跑)。

## 并发安全

同一个 `CompiledGraph` 可被并发 `ainvoke` 多次互不串台 —— 每次新建独立 `GraphSession`,天然继承 rein 的「无状态蓝图」并发安全。

```python
import asyncio
results = await asyncio.gather(*[app.ainvoke({"input": q}, thread_id=f"t{i}")
                                 for i, q in enumerate(questions)])
```
