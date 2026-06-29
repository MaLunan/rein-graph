"""reinGraph 示例:顺序流水线(plan → write → END)+ 打印图拓扑。

演示用 MockProvider(不烧 key、不联网);真实使用把 `provider=MockProvider([...])`
换成 `model="anthropic/claude-opus-4-8"` 即可。
跑:python examples/sequential.py
"""

from rein import Agent, MockProvider

from reingraph import AgentNode, StateGraph


def main() -> None:
    g = StateGraph()
    # plan:读 input,写 output
    g.add_node("plan", Agent(provider=MockProvider(["大纲:1.引子 2.正文 3.结尾"])))
    # write:读上一步的 output,写 article
    g.add_node(
        "write",
        AgentNode(
            "write",
            Agent(provider=MockProvider(["成稿:从前有座山……"])),
            input_key="output",
            output_key="article",
        ),
    )
    g.set_entry_point("plan")
    g.add_edge("plan", "write")
    g.set_finish_point("write")
    app = g.compile()

    print("=== 图拓扑(mermaid)===")
    print(app.to_mermaid())

    r = app.invoke({"input": "写一篇关于 AI 的短文"})
    print("\n=== 结果 ===")
    print("大纲:", r.values["output"])
    print("成稿:", r.values["article"])


if __name__ == "__main__":
    main()
