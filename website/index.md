# reinGraph

> **把多个 [rein](https://github.com/MaLunan/rein) agent 编排成有状态的图工作流** —— 条件分支、循环、并行扇出汇合、人工审批(HITL)。

reinGraph 之于 rein,如同 **LangGraph 之于 LangChain**。但它有一个根本区别 ——

## 区别于 LangGraph:内核全部复用 rein,而非重造

LangGraph 必须**自己造** checkpoint / 状态机 / 中断恢复(因为 LangChain 没有)。
reinGraph **直接继承 rein 的这套机制**:

| 能力 | reinGraph 怎么做 |
|---|---|
| 节点执行 | 调 `rein.Agent.arun` —— 一行没重造 |
| 图 checkpoint | 复用 rein 的 `SessionStore`(存 `GraphSession.model_dump_json()`) |
| 图暂停 / 恢复 | 复用 rein 的 `aresume`(喂回状态从断点继续) |
| 图级中断(HITL) | 把 rein 的 `Interrupt` 原样冒泡到图层 |
| 熔断 | 照抄 rein 的 `check_circuit` 纯函数(超步 / 节点访问 / 超时 / token 四道闸) |

> **reinGraph 新增的只有「图拓扑」这一维**(节点、边、超步引擎、汇合屏障、路由、可视化)。整图(含被中断 agent 的会话、子图的嵌套快照)一句 `model_dump_json` 存盘、`resume` 一层层分发回 `agent.aresume`。

## 30 秒看懂

```python
from reingraph import StateGraph
from rein import Agent

g = StateGraph()
g.add_node("research", Agent(model="anthropic/claude-opus-4-8", system="你负责检索"))
g.add_node("write", Agent(model="anthropic/claude-opus-4-8", system="你负责写作"))
g.set_entry_point("research")
g.add_edge("research", "write")      # research → write 流水线
g.set_finish_point("write")

app = g.compile()
print(app.invoke({"input": "写一篇关于 AI 的短文"}).values["output"])
```

## 能做什么

- **顺序流水线**:A → B → C,数据在节点间流转;
- **条件分支 / 循环**:`routing_fn(state)` 决定下一步,支持 reflexion 式自我反思(带上限熔断);
- **并行扇出 / 汇合**:一个节点扇出到多个 agent 并发,reducer 汇合(map-reduce);
- **图级 HITL**:某个 agent 节点暂停等人审批,整图存盘、换进程恢复;
- **子图**:把一个编译好的图当节点,嵌套复用(含嵌套 HITL);
- **流式 + 可观测**:`astream` 实时事件流,全图用量 / 轨迹聚合;
- **可视化**:`to_mermaid()` 一句话导出拓扑图。

→ 从[快速开始](getting-started.md)上手,或读[核心概念](concepts.md) / [设计哲学](design.md)。
