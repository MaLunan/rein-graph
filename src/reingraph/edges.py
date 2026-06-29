"""边 —— 节点之间的连接(图拓扑)。

- START / END 哨兵 + 静态有向边 Edge(可序列化纯字符串);
- ConditionalEdge:条件边,运行期由 routing_fn(state) 决定去向(G2)。
  routing_fn 是函数 → 不可序列化,所以它不进 GraphSession,而是按 source 名登记在
  CompiledGraph 的运行期注册表里(同 rein 的中间件/路由函数不进序列化的处理)。
"""

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel

START = "__start__"  # 入口虚拟节点(哨兵)
END = "__end__"  # 出口虚拟节点(哨兵)


class Edge(BaseModel):
    """静态有向边(纯字符串,可序列化)。"""

    source: str
    target: str


class ConditionalEdge:
    """条件边:运行期由 routing_fn(state_values) 决定去哪个节点(或 END)。

    routing_fn 返回:
      - 单个字符串(节点名或 END)→ 分支;
      - 字符串列表 → 扇出到多个节点(G3 并行用)。
    path_map(可选):把 routing_fn 的返回值再映射到真实节点名,便于可视化标注。
    """

    def __init__(
        self,
        source: str,
        routing_fn: Callable[[dict[str, Any]], Any],
        path_map: dict[str, str] | None = None,
    ):
        self.source = source
        self.routing_fn = routing_fn
        self.path_map = path_map
