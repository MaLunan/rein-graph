"""GraphConfig —— 图级熔断配置。

照抄 rein.LoopConfig 的「多道闸」哲学,升一维到图:rein 防的是单 agent 的 loop 失控,
reinGraph 防的是【图】失控(节点间无限绕圈、扇出爆炸、总成本失控)。
check_graph_circuit(engine.py)会在每个超步前查这几道闸,任一触顶就安全停。
"""

from pydantic import BaseModel


class GraphConfig(BaseModel):
    """图执行的熔断闸(全部有保守默认,生产可调小)。"""

    max_supersteps: int = 100
    """① 超步闸(对位 rein 的 max_iterations):整张图最多推进多少个超步,防死循环。"""

    max_node_visits: int = 25
    """② 单节点访问闸:任一节点最多被进入多少次。循环节点(reflexion 等)的局部安全网。"""

    timeout_s: float | None = 300
    """③ 墙钟闸:整张图从开始执行起的总超时(秒)。None 表示不限。"""

    max_total_tokens: int | None = None
    """④ 成本闸:各节点 token 用量累加的上限。None 表示不限。"""

    node_timeout_s: float | None = None
    """单个节点的执行超时(秒)。超时算作节点异常 → 触发重试 / 错误中断。None 表示不限。"""

    node_max_retries: int = 0
    """节点异常(含超时)的自动重试次数。瞬时错误(网络抖动 / 限流)自动恢复;
    重试耗尽才转「错误中断」惊动人。默认 0(不自动重试)。中断(审批)不算异常、不重试。"""
