"""节点级超时 + 自动重试测试。"""

import asyncio

from rein import Agent, LoopConfig, MockProvider, ToolCall

from reingraph.config import GraphConfig
from reingraph.graph import StateGraph


def test_自动重试恢复():
    calls = {"n": 0}

    async def flaky(sv):
        calls["n"] += 1
        if calls["n"] <= 2:
            raise ValueError("失败")
        return {"out": "ok"}

    g = StateGraph()
    g.add_node("flaky", flaky)
    g.set_entry_point("flaky")
    g.set_finish_point("flaky")
    r = g.compile(config=GraphConfig(node_max_retries=2)).invoke({"input": "x"})
    assert r.status == "done" and r.values["out"] == "ok"
    assert calls["n"] == 3  # 前 2 次失败,第 3 次成功 —— 自动恢复,没惊动人


def test_重试耗尽转错误中断():
    calls = {"n": 0}

    async def always(sv):
        calls["n"] += 1
        raise RuntimeError("总失败")

    g = StateGraph()
    g.add_node("a", always)
    g.set_entry_point("a")
    g.set_finish_point("a")
    r = g.compile(config=GraphConfig(node_max_retries=1)).invoke({"input": "x"})
    assert r.status == "interrupted" and r.interrupt.inner.type == "error"
    assert calls["n"] == 2  # 重试 1 次 = 总 2 次


def test_超时转错误中断():
    async def slow(sv):
        await asyncio.sleep(0.5)
        return {"out": "done"}

    g = StateGraph()
    g.add_node("s", slow)
    g.set_entry_point("s")
    g.set_finish_point("s")
    r = g.compile(config=GraphConfig(node_timeout_s=0.05)).invoke({"input": "x"})
    assert r.status == "interrupted" and r.interrupt.inner.type == "error"


def test_审批中断不被当异常重试():
    agent = Agent(
        provider=MockProvider([[ToolCall(id="1", name="d", arguments={})]]),
        config=LoopConfig(permission="ask"),
    )

    @agent.tool
    def d() -> str:
        "d"
        return "x"

    g = StateGraph()
    g.add_node("ag", agent)
    g.set_entry_point("ag")
    g.set_finish_point("ag")
    r = g.compile(config=GraphConfig(node_max_retries=3)).invoke({"input": "go"})
    assert r.status == "interrupted" and r.interrupt.inner.type == "need_approval"
