# 图级人工审批(HITL)

让图在某个 agent 节点「暂停等人审批」,整图存盘、换进程恢复 —— 这是 reinGraph 复用 rein 的命门。

```python
from rein import Agent, LoopConfig

from reingraph import FileGraphStore, StateGraph

agent = Agent(model="anthropic/claude-opus-4-8", config=LoopConfig(permission="ask"))

@agent.tool
def refund(amount: int) -> str:
    "给订单退款(危险操作)"
    return do_refund(amount)

g = StateGraph()
g.add_node("handle", agent)
g.set_entry_point("handle")
g.set_finish_point("handle")
app = g.compile(store=FileGraphStore("./sessions"))   # 配 store 才能用 thread_id 恢复

# 第一次:碰到危险工具 → 整图暂停 + 存盘
r = app.invoke({"input": "给订单退款 100"}, thread_id="order-1")
assert r.status == "interrupted"
print(r.interrupt.node, r.interrupt.inner.type)        # handle need_approval

# —— 可以换一个进程:store 里有 order-1 的完整快照 ——
r = app.resume("order-1", approve=True)                # 批准 → 续跑
# r = app.resume("order-1", approve=False)             # 拒绝 → 错误回填,agent 自愈
assert r.status == "done"
```

## 怎么做到的(零新机制)

1. agent 在工具边界因 `permission="ask"` 中断 → rein 产出 `Interrupt` + `Session`;
2. AgentNode 把它**原样冒泡**成图级中断,引擎把 agent 的 `Session` 存进 `GraphSession.node_sessions`;
3. 整图 `GraphSession.model_dump_json()` 存盘(里面嵌着 agent 的会话);
4. `resume` → 找到中断节点 → 调它的 `agent.aresume(...)` —— **直接复用 rein 的恢复**。

支持多轮审批(每次 resume 后可再次中断)、直接传 `session` 恢复(不经 store):

```python
r = app.resume(r.session, approve=True)
```
