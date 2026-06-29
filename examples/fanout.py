"""reinGraph 示例:map-reduce 并行(split 扇出到 3 个视角 worker 并发 → 汇合成稿)。

演示用 MockProvider;真实把 provider 换成 model=... 即可。
跑:python examples/fanout.py
"""

from rein import Agent, MockProvider

from reingraph import AgentNode, StateGraph


def main() -> None:
    g = StateGraph(channels={"drafts": "append"})  # drafts 用 append reducer 汇合多个分支

    async def split(sv):
        return {}

    g.add_node("split", split)
    for i, persona in enumerate(["乐观", "谨慎", "创新"]):
        g.add_node(
            f"w{i}",
            AgentNode(
                f"w{i}",
                Agent(provider=MockProvider([f"{persona}视角:这个方案……"])),
                output_key="drafts",
            ),
        )

    async def merge(sv):
        return {"final": " | ".join(sv["drafts"])}

    g.add_node("merge", merge)
    g.set_entry_point("split")
    for i in range(3):
        g.add_edge("split", f"w{i}")
        g.add_edge(f"w{i}", "merge")
    g.set_finish_point("merge")

    r = g.compile().invoke({"input": "评估这个方案"})
    print("三个视角并发跑完、汇合:")
    print(r.values["final"])


if __name__ == "__main__":
    main()
