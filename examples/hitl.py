"""reinGraph 示例:人工审批(HITL)—— 危险操作前暂停等批准,可换进程恢复。

演示用 MockProvider;真实把 provider 换成 model=... 即可。
跑:python examples/hitl.py
"""

from rein import Agent, LoopConfig, MockProvider, ToolCall

from reingraph import MemoryGraphStore, StateGraph


def main() -> None:
    agent = Agent(
        provider=MockProvider([[ToolCall(id="1", name="refund", arguments={"amount": 100})]]),
        config=LoopConfig(permission="ask"),  # 工具执行前需人工批准
    )

    @agent.tool
    def refund(amount: int) -> str:
        "给订单退款(危险操作)"
        return f"已退款 {amount} 元"

    store = MemoryGraphStore()  # 真实可换成 FileGraphStore / Redis 等
    g = StateGraph()
    g.add_node("handle", agent)
    g.set_entry_point("handle")
    g.set_finish_point("handle")
    app = g.compile(store=store)

    r = app.invoke({"input": "给订单退款 100 元"}, thread_id="order-1")
    print("第一次执行状态:", r.status)  # interrupted —— 整图存进 store 了
    if r.status == "interrupted":
        print("待审批节点:", r.interrupt.node, "/ 类型:", r.interrupt.inner.type)
        # —— 这里可以换一个进程:store 里有 order-1 的完整快照 ——
        r = app.resume("order-1", approve=True)  # 人批准后恢复
        print("批准后恢复状态:", r.status)  # done


if __name__ == "__main__":
    main()
