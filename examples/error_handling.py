"""节点异常处理(生产加固)—— 节点失败的三层防线。

  1. 错误中断:节点抛异常不炸整图 → 转「错误中断」存盘 → resume 重试;
  2. 自动重试:node_max_retries 让瞬时错误(网络抖动 / 限流)自愈,不惊动人;
  3. (超时同理:node_timeout_s 超时也按节点异常处理 → 重试 / 错误中断。)

全程离线可跑。运行:python examples/error_handling.py
"""

from reingraph import GraphConfig, StateGraph


def demo_error_interrupt():
    """节点抛异常 → 错误中断 → resume 重试成功。"""
    calls = {"n": 0}

    async def flaky(sv):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("第一次失败(模拟瞬时错误)")
        return {"out": "成功"}

    g = StateGraph()
    g.add_node("task", flaky)
    g.set_entry_point("task")
    g.set_finish_point("task")
    app = g.compile()
    r = app.invoke({"input": "go"})
    print("① 节点异常 → 错误中断:", r.status, "—", r.interrupt.inner.message)
    r2 = app.resume(r.session, approve=True)  # approve=True 重试该节点
    print("② resume 重试 →", r2.status, ":", r2.values["out"])


def demo_auto_retry():
    """node_max_retries:瞬时错误自动重试,持续失败才升级成错误中断。"""
    calls = {"n": 0}

    async def flaky(sv):
        calls["n"] += 1
        if calls["n"] <= 2:
            raise RuntimeError("瞬时")
        return {"out": "自愈"}

    g = StateGraph()
    g.add_node("task", flaky)
    g.set_entry_point("task")
    g.set_finish_point("task")
    r = g.compile(config=GraphConfig(node_max_retries=2)).invoke({"input": "go"})
    print(f"③ 自动重试(跑了 {calls['n']} 次)→", r.status, ":", r.values["out"])


if __name__ == "__main__":
    demo_error_interrupt()
    demo_auto_retry()
