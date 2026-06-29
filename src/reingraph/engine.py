"""无状态单步引擎 —— 照抄 rein loop.py 的形态:引擎是一组纯函数,状态全在 GraphSession。

  - superstep(gs, compiled):推进【一个超步】= frontier 全员并发跑、合并更新、算下一 frontier。
    任一节点中断 → 整图暂停(同超步已成功的节点照常合并,进度不丢)。
  - arun_graph(gs, compiled):驱动 superstep 循环,每步前 check_graph_circuit 熔断。
  - aresume_graph(gs, compiled, approve, answer):从图级中断恢复 —— 对中断节点调
    node.aresume(内部 agent.aresume,复用 rein),完成则推进图、再中断则多轮审批。
  - check_graph_circuit:图级四道闸纯函数(照抄 rein.circuit.check_circuit)。

engine 不 import CompiledGraph(避免循环),只鸭子式访问 compiled.nodes/.edges/.preds/.conditional/.config。
"""

import asyncio
import time
from typing import Any

from rein import Interrupt

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
    """算一个节点的下游目标:有条件边则调 routing_fn(经 path_map),否则用静态边。"""
    cond = compiled.conditional.get(node)
    if cond is not None:
        result = cond.routing_fn(state_values)
        targets = result if isinstance(result, list) else [result]
        if cond.path_map:
            targets = [cond.path_map.get(t, t) for t in targets]
        return targets
    return list(compiled.edges.get(node, []))


def _compute_next_frontier(compiled: Any, gs: GraphSession, sources: list[str]) -> list[str]:
    """从 sources 的出边算下一 frontier,带汇合屏障(静态前驱未全完成的目标先不进)。"""
    completed_set = set(gs.completed)
    nf: list[str] = []
    for name in sources:
        for t in _next_targets(compiled, name, gs.state.values):
            if t == END or t in nf:
                continue
            preds = compiled.preds.get(t, set())
            if preds and not preds.issubset(completed_set):
                continue  # 汇合屏障:还有上游没完成,先等
            nf.append(t)
    return nf


async def superstep(
    gs: GraphSession, compiled: Any
) -> tuple[GraphSession, list[GraphStep], GraphInterrupt | None]:
    """推进一个超步。返回 (新 gs, 本步流水账, 中断或 None)。"""
    frontier = gs.frontier
    if not frontier:
        gs.done = True
        gs.stop_reason = gs.stop_reason or "done"
        return gs, [], None

    results = await asyncio.gather(
        *[compiled.nodes[n].ainvoke(gs.state.values) for n in frontier],
        return_exceptions=True,  # 节点抛异常不炸整图,作为结果返回(进度保留)
    )

    steps: list[GraphStep] = []
    interrupted: list[tuple[str, Any]] = []
    errored: list[tuple[str, BaseException]] = []
    for name, res in zip(frontier, results, strict=True):
        gs.loop_counts[name] = gs.loop_counts.get(name, 0) + 1
        if isinstance(res, BaseException):
            errored.append((name, res))
            continue
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
            interrupted.append((name, res))

    # 合并所有成功节点(异常/中断时也保留同超步成功节点的进度,顺序固定 → 可复现)
    for name, res in zip(frontier, results, strict=True):
        if isinstance(res, BaseException) or res.interrupt is not None:
            continue
        gs.state = apply_updates(gs.state, res.updates)
        gs.completed.append(name)

    # 节点异常 → 转成「错误中断」(复用 rein 的 error 中断态),整图暂停存盘,resume 可重试/放弃
    if errored:
        first_name, exc = errored[0]
        gs.pending_interrupt = GraphInterrupt(
            node=first_name,
            inner=Interrupt(type="error", message=f"{type(exc).__name__}: {exc}"),
        )
        gs.frontier = [n for n, _ in errored]
        return gs, steps, gs.pending_interrupt

    # 有 agent / 子图中断 → 存断点,整图暂停(frontier 设为待恢复的中断节点)
    if interrupted:
        for name, res in interrupted:
            if res.sub_session is not None:
                gs.sub_sessions[name] = res.sub_session  # 子图节点:存子图快照(嵌套)
            else:
                gs.node_sessions[name] = res.rein_session  # agent 节点:存 rein.Session
        first_name, first_res = interrupted[0]
        gs.pending_interrupt = GraphInterrupt(node=first_name, inner=first_res.interrupt)
        gs.frontier = [n for n, _ in interrupted]
        return gs, steps, gs.pending_interrupt

    # 全成功:算下一 frontier(带汇合屏障)
    gs.frontier = _compute_next_frontier(compiled, gs, frontier)
    gs.superstep += 1
    if not gs.frontier:
        gs.done = True
        gs.stop_reason = "done"
    return gs, steps, None


def _interrupted_result(gs: GraphSession, steps: list[GraphStep]) -> GraphResult:
    gs.stop_reason = "interrupted"
    return GraphResult(
        status="interrupted",
        values=gs.state.values,
        session=gs,
        steps=steps,
        usage=gs.usage,
        stop_reason="interrupted",
        interrupt=gs.pending_interrupt,
    )


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
            return _interrupted_result(gs, all_steps)
    return GraphResult(
        status="done",
        values=gs.state.values,
        session=gs,
        steps=all_steps,
        usage=gs.usage,
        stop_reason=gs.stop_reason,
    )


async def aresume_graph(
    gs: GraphSession, compiled: Any, *, approve: bool = True, answer: str | None = None
) -> GraphResult:
    """从图级中断恢复 —— 复用 rein 的 aresume,零新机制。

    对当前 pending 的中断节点调 node.aresume(内部 agent.aresume):
      - 再次中断(多轮审批)→ 更新断点,继续暂停;
      - 完成 → 清断点、写回 state、推进图,继续 arun_graph(若 frontier 还有其他中断
        节点,superstep 会重新 ainvoke 它们 → 重新中断等审批)。
    """
    if gs.pending_interrupt is None:
        return await arun_graph(gs, compiled)  # 没有待恢复的中断,直接继续

    node_name = gs.pending_interrupt.node
    node = compiled.nodes[node_name]
    is_error = gs.pending_interrupt.inner.type == "error"

    # 错误中断 + 放弃:停止并标记(不重试)
    if is_error and not approve:
        gs.done = True
        gs.stop_reason = "node_error_abandoned"
        gs.pending_interrupt = None
        return GraphResult(
            status="done",
            values=gs.state.values,
            session=gs,
            steps=[],
            usage=gs.usage,
            stop_reason="node_error_abandoned",
        )

    # 重新执行该节点:错误中断 → 重试 ainvoke;agent / 子图中断 → aresume(分流)
    saved: Any
    try:
        if is_error:
            res = await node.ainvoke(gs.state.values)
        elif node_name in gs.sub_sessions:
            res = await node.aresume(gs.sub_sessions[node_name], approve=approve, answer=answer)
        else:
            saved = gs.node_sessions.get(node_name)
            res = await node.aresume(saved, approve=approve, answer=answer)
    except Exception as exc:  # 重试又异常 → 再次错误中断
        gs.pending_interrupt = GraphInterrupt(
            node=node_name, inner=Interrupt(type="error", message=f"{type(exc).__name__}: {exc}")
        )
        return _interrupted_result(gs, [])

    gs.usage = gs.usage + res.usage

    if res.interrupt is not None:  # 再次中断(多轮审批 / 子图再中断,分流存)
        if res.sub_session is not None:
            gs.sub_sessions[node_name] = res.sub_session
        else:
            gs.node_sessions[node_name] = res.rein_session
        gs.pending_interrupt = GraphInterrupt(node=node_name, inner=res.interrupt)
        return _interrupted_result(gs, [])

    # 该节点恢复完成:清断点 + 写回 + 推进
    gs.node_sessions.pop(node_name, None)
    gs.sub_sessions.pop(node_name, None)
    gs.pending_interrupt = None
    gs.state = apply_updates(gs.state, res.updates)
    gs.completed.append(node_name)
    gs.frontier = [n for n in gs.frontier if n != node_name]  # 从待恢复移除
    for t in _compute_next_frontier(compiled, gs, [node_name]):  # 它的下游进 frontier
        if t not in gs.frontier:
            gs.frontier.append(t)
    gs.superstep += 1
    gs.done = False
    gs.stop_reason = None
    return await arun_graph(gs, compiled)  # 继续跑


async def astream_graph(gs: GraphSession, compiled: Any):
    """边推进边 yield GraphEvent(超步级)。逻辑同 arun_graph,只是每步发事件。"""
    from reingraph.stream import GraphEvent

    start = time.monotonic()
    while not gs.done:
        reason = check_graph_circuit(gs, compiled.config, start)
        if reason:
            gs.done = True
            gs.stop_reason = reason
            break
        if not gs.frontier:
            gs.done = True
            gs.stop_reason = gs.stop_reason or "done"
            break
        yield GraphEvent(type="superstep_start", superstep=gs.superstep)
        for n in gs.frontier:  # 跑前的 frontier = 本超步要跑的节点
            yield GraphEvent(type="node_start", node=n, superstep=gs.superstep)
        gs, steps, interrupt = await superstep(gs, compiled)
        for s in steps:
            yield GraphEvent(
                type="node_end",
                node=s.node,
                superstep=s.superstep,
                usage=s.usage,
                summary=s.summary,
            )
        if interrupt is not None:
            yield GraphEvent(type="interrupt", node=interrupt.node, superstep=gs.superstep)
            return
        yield GraphEvent(type="state_update", superstep=gs.superstep, values=dict(gs.state.values))
    yield GraphEvent(
        type="done", values=dict(gs.state.values), usage=gs.usage, stop_reason=gs.stop_reason
    )
