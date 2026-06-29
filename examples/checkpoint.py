"""存盘 + 跨进程恢复 —— reinGraph 的命门(复用 rein 的 checkpoint 心法)。

含一个 permission="ask" 的审批节点:图跑到审批边界中断 → 存盘到磁盘 →
【模拟换一个进程】用全新的 CompiledGraph + 从磁盘 load 出的 GraphSession 恢复 → 批准后完成。

证明:整图(含被中断 agent 的会话)一句 model_dump_json 就能存盘、换进程 resume。
全程 MockProvider —— 离线可跑。运行:python examples/checkpoint.py
"""

import tempfile
from pathlib import Path

from rein import Agent, LoopConfig, MockProvider, ToolCall

from reingraph import FileGraphStore, StateGraph


def build(responses):
    # MockProvider 是有状态的(按顺序消费 responses);真实 provider 无状态,不需要这样区分。
    agent = Agent(provider=MockProvider(responses), config=LoopConfig(permission="ask"))

    @agent.tool
    def deploy() -> str:
        "部署到生产环境"
        return "deployed"

    g = StateGraph()
    g.add_node("ops", agent)
    g.set_entry_point("ops")
    g.set_finish_point("ops")
    return g


if __name__ == "__main__":
    tmp = Path(tempfile.mkdtemp())
    store = FileGraphStore(tmp)

    # 进程 1:MockProvider 先返回工具调用 → ask 审批中断 → 存盘
    app1 = build([[ToolCall(id="1", name="deploy", arguments={})], "部署完成"]).compile()
    r1 = app1.invoke({"input": "上线新版本"}, thread_id="deploy-1")
    store.save("deploy-1", r1.session)
    print("① 中断:", r1.status, "—", r1.interrupt.inner.type, "@节点", r1.interrupt.node)
    print("   已存盘 →", tmp / "deploy-1.json")

    # 进程 2:全新 app(模拟换进程)+ 从磁盘 load 回 → 批准恢复(批准后执行工具 → 返回总结)
    app2 = build(["部署完成"]).compile()
    gs = store.load("deploy-1")
    print("② 从磁盘读回 GraphSession:thread_id =", gs.thread_id, "frontier =", gs.frontier)
    r2 = app2.resume(gs, approve=True)
    print("③ 批准后完成:", r2.status, "—", r2.values["output"])
