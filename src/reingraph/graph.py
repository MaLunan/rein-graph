"""StateGraph —— 图的构建器(混合 API:LangGraph 方法链 + rein 的 @graph.node 装饰器糖)。

add_node 智能适配:传 rein.Agent → 自动包 AgentNode;传 async 函数 → FunctionNode;
传已实现 ainvoke 的对象 → 直接当 Node 收(鸭子)。
compile() 做编译期校验(有入口、边端点都存在)→ 产出可执行的 CompiledGraph。
"""

from collections.abc import Callable
from typing import Any

from rein import Agent

from reingraph.edges import END, START
from reingraph.nodes import AgentNode, FunctionNode, Node


class StateGraph:
    """图构建器。链式 add_node / add_edge / set_entry_point / set_finish_point,最后 compile()。"""

    def __init__(self, channels: dict[str, str] | list[str] | None = None):
        self._nodes: dict[str, Node] = {}
        self._edges: dict[str, list[str]] = {}  # source -> [targets](含 START/END 哨兵)
        self._channels = channels  # 传给 make_state(声明各键的合并 reducer)
        self._entry: str | None = None

    def add_node(self, name: str, node: Any) -> "StateGraph":
        """登记节点。智能适配:Agent→AgentNode、async 函数→FunctionNode、已是 Node→直接收。"""
        if isinstance(node, Agent):
            node = AgentNode(name, node)
        elif hasattr(node, "ainvoke"):
            pass  # 已实现节点协议,直接收(鸭子类型)
        elif callable(node):
            node = FunctionNode(name, node)
        else:
            raise TypeError(f"无法把 {type(node).__name__} 当作节点(需 Agent / async 函数 / Node)")
        node.name = name
        self._nodes[name] = node
        return self

    def add_edge(self, source: str, target: str) -> "StateGraph":
        """加一条静态有向边。source=START 即把 target 设为入口。"""
        self._edges.setdefault(source, []).append(target)
        if source == START:
            self._entry = target
        return self

    def add_conditional_edges(
        self, source: str, routing_fn: Callable, path_map: dict | None = None
    ):
        """条件边(运行期由 routing_fn(state) 决定去向)—— G2 实现。"""
        raise NotImplementedError("条件边将在 G2 实现")

    def set_entry_point(self, name: str) -> "StateGraph":
        """设入口(等价 add_edge(START, name))。"""
        return self.add_edge(START, name)

    def set_finish_point(self, name: str) -> "StateGraph":
        """设出口(等价 add_edge(name, END))。"""
        return self.add_edge(name, END)

    def node(self, name: str | None = None) -> Callable:
        """@graph.node 装饰器糖:把一个 async 函数登记成节点。

        @graph.node("research")
        async def research(state): return {"notes": ...}
        """

        def deco(fn: Callable) -> Callable:
            self.add_node(name or fn.__name__, fn)
            return fn

        return deco

    def compile(self, *, config: Any = None, store: Any = None) -> Any:
        """编译期校验 + 冻结成 CompiledGraph。校验失败立即抛错(快速失败)。"""
        from reingraph.compiled import CompiledGraph
        from reingraph.config import GraphConfig

        if self._entry is None:
            raise ValueError("图缺少入口:用 set_entry_point(name) 或 add_edge(START, name)")
        valid = set(self._nodes) | {START, END}
        for src, targets in self._edges.items():
            if src not in valid:
                raise ValueError(f"边的起点 '{src}' 不是已注册节点")
            for t in targets:
                if t not in valid:
                    raise ValueError(f"边的终点 '{t}' 不是已注册节点或 END")
        return CompiledGraph(
            nodes=self._nodes,
            edges=self._edges,
            entry=self._entry,
            channels=self._channels,
            config=config or GraphConfig(),
            store=store,
        )
