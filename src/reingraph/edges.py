"""边 —— 节点之间的连接(图拓扑)。

G1 先做基础:START / END 哨兵 + 静态有向边 Edge(纯字符串,可序列化)。
条件边 / 扇出 / 汇合 / 循环在 G2-G3 加 —— 它们统一用「边 + routing_fn 返回值」表达,
所以这里的基础结构不会被推翻。
"""

from pydantic import BaseModel

START = "__start__"  # 入口虚拟节点(哨兵):add_edge(START, x) 即把 x 设为入口
END = "__end__"  # 出口虚拟节点(哨兵):add_edge(x, END) 即把 x 设为出口


class Edge(BaseModel):
    """静态有向边(纯字符串,可序列化)。"""

    source: str
    target: str
