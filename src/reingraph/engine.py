"""无状态单步引擎 —— 照抄 rein loop.py 的形态:引擎是一组纯函数,状态全在 GraphSession。

  - superstep(gs, compiled):推进【一个超步】= 把当前 frontier 的所有节点并发跑一遍,
    合并各自的状态更新,算出下一个 frontier。任一节点中断 → 整图暂停(存断点)。
  - arun_graph(gs, compiled):驱动 superstep 循环,每步前 check_graph_circuit 熔断。
  - check_graph_circuit:图级四道闸纯函数(照抄 rein.circuit.check_circuit)。

G1 的顺序图里 frontier 通常只有一个节点,但这里就按「frontier 全员并发」写,
G3 的并行扇出/汇合天然复用同一套(只需再加汇合屏障),不必重写。

注:engine 不 import CompiledGraph(避免循环),只鸭子式访问 compiled.nodes / .edges / .config。
"""

import asyncio
import time
from typing import Any

from reingraph.config import GraphConfig
from reingraph.edges import END
from reingraph.result import GraphInterrupt, GraphStep
from reingraph.session import GraphResult, GraphSession
from reingraph.state import apply_updates


def check_graph_circuit(gs: GraphSession, config: GraphConfig, start_time: float) -> str | None:
    """图级四道闸熔断(纯函数,照抄 rein 形态)。任一触顶返回 stop_reason,否则 None。"""
    if gs.superstep >= config.max_supersteps:  # ① 超步闸
        return "max_supersteps"
    if (
        config.timeout_s is not None and (time.monotonic() - start_time) >= config.timeout_s
    ):  # ③ 超时
        return "timeout"
    if config.max_total_tokens is not None:  # ④ token 成本闸
        if gs.usage.input_tokens + gs.usage.output_tokens >= config.max_total_tokens:
            return "max_tokens"
    for cnt in gs.loop_counts.values():  # ② 单节点访问闸
        if cnt >= config.max_node_visits:
            return "max_node_visits"
    return None


def _next_targets(compiled: Any, node: str, state_values: dict[str, Any]) -> list[str]:
    """算一个节点的下游目标。
    - 有条件边:调 routing_fn(state) 得目标(单个或列表),经 path_map 映射(G2);
    - 否则:用静态边。
    """
    cond = compiled.conditional.get(node)
    if cond is not None:
        result = cond.routing_fn(state_values)
        targets = result if isinstance(result, list) else [result]
        if cond.path_map:
            targets = [cond.path_map.get(t, t) for t in targets]
        return targets
    return list(compiled.edges.get(node, []))


async def superstep(
    gs: GraphSession, compiled: Any
) -> tuple[GraphSession, list[GraphStep], GraphInterrupt | None]:
    """推进一个超步。返回 (新 gs, 本步流水账, 中断或 None)。"""
    frontier = gs.frontier
    if not frontier:
        gs.done = True
        gs.stop_reason = gs.stop_reason or "done"
        return gs, [], None

    # frontier 全员并发跑(G1 顺序图通常单个;并发是 G3 并行的形状)
    results = await asyncio.gather(*[compiled.nodes[n].ainvoke(gs.state.values) for n in frontier])

    steps: list[GraphStep] = []
    # 先扫一遍:记流水账 + 累加用量 + 计数;任一中断则整图暂停
    for name, res in zip(frontier, results, strict=True):
        gs.loop_counts[name] = gs.loop_counts.get(name, 0) + 1
        gs.usage = gs.usage + res.usage
        steps.append(
            GraphStep(
                superstep=gs.superstep,
                node=name,
                summary=res.summary,
                inner_steps=res.steps,
                usage=res.usage,
            )
        )
        if res.interrupt is not None:
            gs.node_sessions[name] = res.rein_session  # 存断点(rein.Session)
            gs.pending_interrupt = GraphInterrupt(node=name, inner=res.interrupt)
            return gs, steps, gs.pending_interrupt  # 任一中断 → 整图暂停(frontier 不动)

    # 全部成功:按 frontier 顺序合并 updates(顺序固定 → 可复现),算下一 frontier
    next_frontier: list[str] = []
    for name, res in zip(frontier, results, strict=True):
        gs.state = apply_updates(gs.state, res.updates)
        gs.completed.append(name)
        for t in _next_targets(compiled, name, gs.state.values):
            if t != END and t not in next_frontier:
                next_frontier.append(t)

    gs.frontier = next_frontier
    gs.superstep += 1
    if not gs.frontier:
        gs.done = True
        gs.stop_reason = "done"
    return gs, steps, None


async def arun_graph(gs: GraphSession, compiled: Any) -> GraphResult:
    """驱动 superstep 循环,每步前熔断检查。中断时不置 done(可恢复)。"""
    start = time.monotonic()
    all_steps: list[GraphStep] = []
    while not gs.done:
        reason = check_graph_circuit(gs, compiled.config, start)
        if reason:
            gs.done = True
            gs.stop_reason = reason
            break
        gs, steps, interrupt = await superstep(gs, compiled)
        all_steps.extend(steps)
        if interrupt is not None:
            gs.stop_reason = "interrupted"
            return GraphResult(
                status="interrupted",
                values=gs.state.values,
                session=gs,
                steps=all_steps,
                usage=gs.usage,
                stop_reason="interrupted",
                interrupt=interrupt,
            )
    return GraphResult(
        status="done",
        values=gs.state.values,
        session=gs,
        steps=all_steps,
        usage=gs.usage,
        stop_reason=gs.stop_reason,
    )
