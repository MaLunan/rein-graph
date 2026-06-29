"""reinGraph —— 图编排框架:把多个 rein agent 编排成有状态的图工作流。

定位类比:reinGraph 之于 rein,如同 LangGraph 之于 LangChain。
但根本区别在于 ——【内核全部复用 rein,而非重造】:
  - 图的 checkpoint 复用 rein 的 SessionStore;
  - 图的暂停/恢复复用 rein 的 aresume(喂回状态从断点继续);
  - 节点内执行复用 rein 的 Agent.arun / RunResult;
  - 图级中断复用 rein 的 Interrupt(原样冒泡);
  - 熔断照抄 rein 的 check_circuit 纯函数形态。
reinGraph 新增的只有「图拓扑」这一维。

最小用法:
    from reingraph import StateGraph
    from rein import Agent

    g = StateGraph()
    g.add_node("write", Agent(model="anthropic/claude-opus-4-8"))
    g.set_entry_point("write")
    g.set_finish_point("write")
    app = g.compile()
    print(app.invoke({"input": "写一首诗"}).values["output"])
"""

__version__ = "0.1.0"

from reingraph.config import GraphConfig
from reingraph.edges import END, START
from reingraph.graph import StateGraph
from reingraph.nodes import AgentNode, FunctionNode, Node, NodeResult
from reingraph.result import GraphInterrupt, GraphStep
from reingraph.session import GraphResult, GraphSession
from reingraph.state import (
    Channel,
    GraphState,
    apply_updates,
    make_state,
    register_reducer,
)
from reingraph.store import FileGraphStore, GraphStore, MemoryGraphStore
from reingraph.stream import GraphEvent

__all__ = [
    "__version__",
    # 构建 / 执行
    "StateGraph",
    "START",
    "END",
    "GraphConfig",
    # 状态
    "GraphState",
    "Channel",
    "make_state",
    "apply_updates",
    "register_reducer",
    # 节点
    "Node",
    "NodeResult",
    "AgentNode",
    "FunctionNode",
    # 快照 / 结果 / 中断
    "GraphSession",
    "GraphResult",
    "GraphInterrupt",
    "GraphStep",
    # 持久化(复用 rein.SessionStore 形态)
    "GraphStore",
    "MemoryGraphStore",
    "FileGraphStore",
    # 流式
    "GraphEvent",
]
