"""图执行的中断与流水账模型。

核心做法:【直接复用 rein 的 Interrupt / Step / Usage】,只在外面包一层「是哪个节点」。
这正是 reinGraph「复用而非重造」的体现 —— 图级 HITL 不发明新的中断类型,
而是把单 agent 的 rein.Interrupt 原样抬到图层,额外记一个 node 名而已。

注:整图结果 GraphResult 依赖 GraphSession(session.py),为避免循环依赖,
放在 session.py(G1)里定义。
"""

from typing import Literal

from pydantic import BaseModel, Field
from rein import Interrupt, Step, Usage  # ← 直接复用 rein 的中断/流水账/用量类型


class GraphInterrupt(BaseModel):
    """图级中断:记录「哪个节点中断了」+ 内层的 rein.Interrupt(原样复用,不翻译)。

    恢复时:引擎据 node 找到该节点存下的 rein.Session,调 agent.aresume —— 全程复用 rein。
    """

    node: str  # 中断发生在哪个节点
    inner: Interrupt  # 复用 rein.Interrupt(type: need_approval / need_input / error)


class GraphStep(BaseModel):
    """图级流水账:一个节点跑完一次的记录,内嵌该节点 agent 的 rein.Step(可观测聚合)。

    整图的 steps = 各节点 GraphStep 的有序拼接;每个 GraphStep 里的 inner_steps
    就是那个 agent 本次 run 的逐步明细 —— 图层只负责标注「这些步属于哪个节点/哪个超步」。
    """

    superstep: int  # 第几个超步产生的
    node: str  # 哪个节点
    kind: Literal["node"] = "node"
    summary: str = ""  # 简短摘要(如节点输出前 120 字)
    inner_steps: list[Step] = Field(default_factory=list)  # 复用 rein.Step(该节点内部明细)
    usage: Usage = Field(default_factory=Usage)  # 复用 rein.Usage(该节点用量)
