"""nodes.py 测试:AgentNode(文本/中断冒泡/aresume)+ FunctionNode + NodeResult 序列化。

全程 MockProvider —— 不联网、不烧 token、确定性(同 rein 的测试范式)。
"""

import asyncio

from rein import Agent, LoopConfig, MockProvider, ToolCall

from reingraph.nodes import AgentNode, FunctionNode, NodeResult


def _run(coro):
    return asyncio.run(coro)


def _ask_agent() -> Agent:
    """造一个会在工具边界因 permission='ask' 中断的 agent。"""
    agent = Agent(
        provider=MockProvider([[ToolCall(id="1", name="danger", arguments={})]]),
        config=LoopConfig(permission="ask"),
    )

    @agent.tool
    def danger() -> str:
        "危险操作"
        return "done"

    return agent


def test_agentnode_文本输出():
    node = AgentNode("n1", Agent(provider=MockProvider(["回答A"])), input_key="q", output_key="a")
    r = _run(node.ainvoke({"q": "问题"}))
    assert r.updates["a"] == "回答A"
    assert r.interrupt is None


def test_agentnode_prompt_fn拼装():
    node = AgentNode(
        "n", Agent(provider=MockProvider(["ok"])), prompt_fn=lambda sv: f"{sv['a']}-{sv['b']}"
    )
    r = _run(node.ainvoke({"a": "x", "b": "y"}))
    assert r.updates["output"] == "ok"


def test_agentnode_中断冒泡():
    node = AgentNode("n2", _ask_agent())
    r = _run(node.ainvoke({"input": "do it"}))
    assert r.interrupt is not None
    assert r.interrupt.type == "need_approval"
    assert r.rein_session is not None  # 断点存下,resume 时喂回 agent.aresume


def test_agentnode_aresume续跑():
    node = AgentNode("n2", _ask_agent())
    r = _run(node.ainvoke({"input": "do it"}))
    r2 = _run(node.aresume(r.rein_session, approve=True, answer=None))
    assert r2.interrupt is None  # 批准后跑完,不再中断


def test_functionnode():
    async def f(sv):
        return {"x": sv.get("n", 0) + 1}

    r = _run(FunctionNode("f", f).ainvoke({"n": 5}))
    assert r.updates["x"] == 6


def test_functionnode_返回None视为无更新():
    async def f(sv):
        return None

    r = _run(FunctionNode("f", f).ainvoke({}))
    assert r.updates == {}


def test_noderesult_序列化含rein_session():
    node = AgentNode("n", _ask_agent())
    r = _run(node.ainvoke({"input": "x"}))
    back = NodeResult.model_validate_json(r.model_dump_json())
    assert back.interrupt is not None
    assert back.rein_session is not None  # 嵌套的 rein.Session 也能往返
