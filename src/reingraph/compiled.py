"""CompiledGraph —— 编译后的可执行图。

持有冻结的拓扑(nodes / edges / entry)+ 配置 + 可选持久化 store,提供执行入口。
执行委托给无状态的 engine(同步门面照抄 rein:已在事件循环里则报错引导 ainvoke)。
aresume(图级 HITL 恢复)在 G4 实现。
"""

import asyncio
from typing import Any

from reingraph import engine
from reingraph.config import GraphConfig
from reingraph.nodes import Node
from reingraph.session import GraphResult, GraphSession
from reingraph.state import make_state


class CompiledGraph:
    """编译产物:可被 invoke / ainvoke 执行的图。"""

    def __init__(
        self,
        *,
        nodes: dict[str, Node],
        edges: dict[str, list[str]],
        entry: str,
        channels: Any,
        config: GraphConfig,
        store: Any,
    ):
        self.nodes = nodes
        self.edges = edges
        self.entry = entry
        self.channels = channels
        self.config = config
        self.store = store

    async def ainvoke(self, inputs: dict[str, Any], *, thread_id: str = "default") -> GraphResult:
        """异步执行一张图:把 inputs 灌进初始状态,从 entry 起跑到 END。"""
        state = make_state(self.channels, inputs)
        gs = GraphSession(thread_id=thread_id, state=state, frontier=[self.entry])
        result = await engine.arun_graph(gs, self)
        if self.store is not None:  # 配了 store 就把最终/中断快照存盘
            self.store.save(thread_id, result.session)
        return result

    def invoke(self, inputs: dict[str, Any], *, thread_id: str = "default") -> GraphResult:
        """同步门面。已在事件循环中(Jupyter/Web)则报错,引导用 ainvoke(不嵌套 event loop)。"""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.ainvoke(inputs, thread_id=thread_id))
        raise RuntimeError("已在事件循环中,请改用 await ainvoke(...)")
