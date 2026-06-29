"""图级流式事件 —— astream 把图执行变成实时事件流,UI 可边跑边显示。

事件粒度:超步级(超步开始 / 节点开始 / 节点结束 / 状态更新 / 中断 / 完成)。
AgentNode 内部 rein 的 token 级流式(agent.astream)可作为 chunk 透传 —— 留作后续增强,
G5 先做超步级事件(对编排可观测已足够)。
"""

from typing import Any, Literal

from pydantic import BaseModel
from rein import StreamChunk, Usage


class GraphEvent(BaseModel):
    """图执行过程中的一个事件。"""

    type: Literal[
        "superstep_start",  # 一个超步开始
        "node_start",  # 某节点开始跑
        "node_end",  # 某节点跑完
        "state_update",  # 一个超步合并后的状态快照
        "interrupt",  # 图级中断(等审批)
        "done",  # 图执行结束
    ]
    node: str | None = None
    superstep: int = 0
    values: dict[str, Any] | None = None  # state_update / done 时的状态快照
    usage: Usage | None = None  # node_end / done 时的用量
    chunk: StreamChunk | None = None  # (预留)透传 AgentNode 内部 rein 流式
    stop_reason: str | None = None  # done 时
    summary: str | None = None  # node_end 时的简短摘要
