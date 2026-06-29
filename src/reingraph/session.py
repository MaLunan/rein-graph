"""图执行的可序列化快照(GraphSession)与结果(GraphResult)。

GraphSession 对位 rein.Session,升一维到图:全可序列化、零业务方法。
【命门】node_sessions: dict[节点名, rein.Session] —— 被中断的 AgentNode 的会话整个嵌进来。
于是:
  - 图存盘  = GraphSession.model_dump_json()(rein.Session 本就可序列化,嵌进来天然可序列化);
  - 图恢复  = 读回 GraphSession,对中断节点调 agent.aresume(node_sessions[node])。
零新机制 —— 这是「图级 HITL 复用 rein 单 agent 中断」的全部秘密。

GraphResult 对位 rein.RunResult,放这里(依赖 GraphSession)。
"""

from typing import Any, Literal

from pydantic import BaseModel, Field
from rein import Session, Usage

from reingraph.result import GraphInterrupt, GraphStep
from reingraph.state import GraphState


class GraphSession(BaseModel):
    """一次图执行的全部状态(可序列化快照)。暂停 = 存它,恢复 = 喂回它。"""

    thread_id: str = "default"
    state: GraphState = Field(default_factory=GraphState)  # 共享黑板
    frontier: list[str] = Field(default_factory=list)  # 当前待执行的节点(并行时多个)
    completed: list[str] = Field(default_factory=list)  # 已完成节点(汇合屏障 / 可观测)
    superstep: int = 0  # 已推进的超步数(熔断第①闸)
    node_sessions: dict[str, Session] = Field(default_factory=dict)  # 命门:中断节点的 rein.Session
    sub_sessions: dict[str, "GraphSession"] = Field(
        default_factory=dict
    )  # 子图节点中断时存的子图快照(嵌套)
    loop_counts: dict[str, int] = Field(default_factory=dict)  # 各节点进入次数(循环上限闸)
    usage: Usage = Field(default_factory=Usage)  # 图级累计用量(复用 rein.Usage 相加)
    pending_interrupt: GraphInterrupt | None = None  # 图级中断详情(谁中断了)
    done: bool = False
    stop_reason: str | None = (
        None  # done / max_supersteps / max_node_visits / timeout / interrupted
    )


class GraphResult(BaseModel):
    """一次图执行的结果。对位 rein.RunResult。"""

    status: Literal["done", "interrupted"]
    values: dict[str, Any] = Field(default_factory=dict)  # 最终 GraphState.values(便捷取结果)
    session: GraphSession  # 完整快照(可存盘 / 可 resume)
    steps: list[GraphStep] = Field(default_factory=list)  # 图级流水账
    usage: Usage = Field(default_factory=Usage)  # 图级总用量
    stop_reason: str | None = None
    interrupt: GraphInterrupt | None = None  # 若 status="interrupted"

    def __str__(self) -> str:
        return str(self.values)
