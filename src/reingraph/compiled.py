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
        conditional: dict | None = None,
    ):
        self.nodes = nodes
        self.edges = edges
        self.entry = entry
        self.channels = channels
        self.config = config
        self.store = store
        self.conditional = conditional or {}  # source -> ConditionalEdge(运行期,不序列化)
        # 汇合屏障用:每个节点的静态前驱集合(排除 START 虚拟入口)。
        # 一个节点只有当【所有】静态前驱都完成,才被放进 frontier —— 防不对称汇合提前跑。
        from reingraph.edges import END, START

        self.preds: dict[str, set[str]] = {}
        for src, targets in edges.items():
            if src == START:
                continue
            for t in targets:
                if t != END:
                    self.preds.setdefault(t, set()).add(src)

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

    async def aresume(
        self,
        session_or_thread: "GraphSession | str",
        *,
        approve: bool = True,
        answer: str | None = None,
    ) -> GraphResult:
        """从图级中断恢复。参数可传 GraphSession 对象,或 thread_id(从 store 读回)。"""
        if isinstance(session_or_thread, str):
            if self.store is None:
                raise ValueError("传 thread_id 恢复需要在 compile(store=...) 配 store")
            gs = self.store.load(session_or_thread)
            if gs is None:
                raise ValueError(f"找不到 thread_id={session_or_thread!r} 的快照")
        else:
            gs = session_or_thread
        result = await engine.aresume_graph(gs, self, approve=approve, answer=answer)
        if self.store is not None:
            self.store.save(result.session.thread_id, result.session)
        return result

    def resume(
        self,
        session_or_thread: "GraphSession | str",
        *,
        approve: bool = True,
        answer: str | None = None,
    ) -> GraphResult:
        """同步 resume 门面(在事件循环里则报错引导 aresume)。"""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.aresume(session_or_thread, approve=approve, answer=answer))
        raise RuntimeError("已在事件循环中,请改用 await aresume(...)")

    async def astream(self, inputs: dict[str, Any], *, thread_id: str = "default"):
        """流式执行:逐个 yield 图级 GraphEvent(超步 / 节点 / 状态 / 中断 / 完成)。"""
        state = make_state(self.channels, inputs)
        gs = GraphSession(thread_id=thread_id, state=state, frontier=[self.entry])
        async for ev in engine.astream_graph(gs, self):
            yield ev
        if self.store is not None:
            self.store.save(thread_id, gs)
