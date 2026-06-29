"""节点 —— 图的执行单元。

统一协议:每个节点都实现 `ainvoke(读 state) -> NodeResult`。引擎不关心节点种类(鸭子类型,
开闭原则,同 rein 的 Provider/Runtime)。

三种内置节点:
- AgentNode:包一个 rein.Agent ——【reinGraph 复用 rein 的最核心落点】,一次把
  arun / aresume / RunResult / Interrupt / Session / usage / steps 全用上,没重造任何一项。
- FunctionNode:包一个普通 async 函数,做纯编排粘合(取数/转换/路由前预处理,不涉及 LLM)。
- SubGraphNode:包一个 CompiledGraph 作子图 —— 依赖 compiled.py,放到 G6 实现。

NodeResult(节点跑完一次的结果)直接复用 rein 的 Interrupt / Usage / Session / Step。
"""

from collections.abc import Awaitable, Callable
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field
from rein import Agent, Interrupt, RunResult, Session, Step, Usage


class NodeResult(BaseModel):
    """一个节点跑完一次的结果(可序列化)。"""

    updates: dict[str, Any] = Field(default_factory=dict)  # 写回 GraphState 的部分更新
    interrupt: Interrupt | None = None  # 复用 rein.Interrupt —— 图级中断的种子
    rein_session: Session | None = None  # AgentNode 中断时存的 rein.Session(resume 时喂回)
    usage: Usage = Field(default_factory=Usage)  # 复用 rein.Usage
    steps: list[Step] = Field(default_factory=list)  # 复用 rein.Step(可观测)
    summary: str = ""  # 简短摘要(给流水账)


@runtime_checkable
class Node(Protocol):
    """节点协议:引擎只认这个签名。任何实现了它的对象都能当节点(鸭子类型)。"""

    name: str

    async def ainvoke(self, state_values: dict[str, Any]) -> NodeResult: ...

    async def aresume(
        self, node_session: Session, *, approve: bool, answer: str | None
    ) -> NodeResult: ...


class AgentNode:
    """把一个 rein.Agent 包成图节点 —— reinGraph 复用 rein 的命门。"""

    def __init__(
        self,
        name: str,
        agent: Agent,
        *,
        input_key: str = "input",  # 默认从 state.values[input_key] 取 prompt
        output_key: str = "output",  # 把 RunResult.output 写回 state[output_key]
        prompt_fn: Callable[[dict[str, Any]], str] | None = None,  # 自定义 prompt 拼装
    ):
        self.name = name
        self.agent = agent
        self.input_key = input_key
        self.output_key = output_key
        self.prompt_fn = prompt_fn

    def _prompt(self, state_values: dict[str, Any]) -> str:
        """从图状态取出喂给 agent 的 prompt:优先 prompt_fn,否则取 input_key。"""
        if self.prompt_fn is not None:
            return self.prompt_fn(state_values)
        return str(state_values.get(self.input_key, ""))

    def _from_result(self, result: RunResult) -> NodeResult:
        """把 rein 的 RunResult 转成 NodeResult。中断则原样冒泡,完成则写回输出。"""
        if result.status == "interrupted":
            msg = result.interrupt.message if result.interrupt else ""
            return NodeResult(
                interrupt=result.interrupt,  # ← 中断原样冒泡,不翻译
                rein_session=result.session,  # ← 存断点;resume 时喂回 agent.aresume
                usage=result.usage,
                steps=result.steps,
                summary=f"[interrupted] {msg}",
            )
        return NodeResult(
            updates={self.output_key: result.output},
            usage=result.usage,
            steps=result.steps,
            summary=(result.output or "")[:120],
        )

    async def ainvoke(self, state_values: dict[str, Any]) -> NodeResult:
        result = await self.agent.arun(self._prompt(state_values))  # ← 直接调 rein
        return self._from_result(result)

    async def aresume(
        self, node_session: Session, *, approve: bool, answer: str | None
    ) -> NodeResult:
        # ← 复用 rein 的 aresume:喂回该节点存下的 Session,从断点续跑(可能再次中断 = 多轮审批)
        result = await self.agent.aresume(node_session, approve=approve, answer=answer)
        return self._from_result(result)


class FunctionNode:
    """把一个普通 async 函数包成图节点:`async fn(state_values) -> dict 更新 | None`。

    用于纯编排粘合(取数、格式转换、路由前预处理),不涉及 LLM,因此永不产生中断。
    """

    def __init__(
        self,
        name: str,
        fn: Callable[[dict[str, Any]], Awaitable[dict[str, Any] | None]],
    ):
        self.name = name
        self.fn = fn

    async def ainvoke(self, state_values: dict[str, Any]) -> NodeResult:
        updates = await self.fn(state_values)
        return NodeResult(updates=updates or {}, summary=f"fn:{self.name}")

    async def aresume(
        self, node_session: Session, *, approve: bool, answer: str | None
    ) -> NodeResult:
        # 函数节点不产生中断,理论上不会被 resume(防御性报错,而非静默)。
        raise NotImplementedError("FunctionNode 不产生中断,不应被 resume")
