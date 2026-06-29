"""流式:astream 在图执行过程中逐个发事件,实时看进度(复用 rein 的 astream 心法,升到图级)。

全程 MockProvider —— 离线可跑。运行:python examples/streaming.py
"""

import asyncio

from rein import Agent, MockProvider

from reingraph import StateGraph


async def main():
    g = StateGraph()
    g.add_node("plan", Agent(provider=MockProvider(["大纲完成"])))
    g.add_node("write", Agent(provider=MockProvider(["正文完成"])))
    g.set_entry_point("plan")
    g.add_edge("plan", "write")
    g.set_finish_point("write")
    app = g.compile()

    print("事件流:")
    async for ev in app.astream({"input": "写文章"}):
        node = getattr(ev, "node", None) or "-"
        print(f"  · {ev.type:12} @ {node}")


if __name__ == "__main__":
    asyncio.run(main())
