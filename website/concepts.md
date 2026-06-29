# 核心概念

reinGraph 全部沿用 rein 的「纯数据可序列化 + 无状态推进」心法,只在「节点之间」加了图拓扑。

## StateGraph(构建器)

混合 API:LangGraph 熟悉的方法链 + rein 的装饰器糖。

```python
g = StateGraph(channels={"drafts": "append"})   # 可选:声明状态键的合并规则
g.add_node("a", agent_or_fn)                     # 智能适配 Agent / 函数 / 子图
g.add_edge("a", "b")                             # 静态边
g.add_conditional_edges("a", routing_fn)         # 条件边
g.set_entry_point("a"); g.set_finish_point("b")
app = g.compile()                                # 编译期校验 → CompiledGraph

@g.node("x")                                     # 装饰器糖
async def x(state): ...
```

## GraphState:共享黑板(channel + reducer)

所有节点读写的一块状态。节点输出一个「部分更新」`{key: 值}`,引擎按各键的 **reducer** 合并:

| reducer | 行为 | 场景 |
|---|---|---|
| `last_write_wins`(默认) | 后写覆盖 | 顺序图 |
| `append` | 列表追加 | 并行汇合(每个分支 append 自己的产出) |
| `add` | 数值累加 | 计数 / 打分 |
| `merge_dict` | 字典浅合并 | 多分支各写若干键 |

> 关键:reducer 用**名字**(查注册表)而非函数存,所以整块状态可 `model_dump_json()` —— 这是图能 checkpoint 的地基。

## 边:静态 / 条件

- **静态边** `add_edge(a, b)`:固定从 a 到 b。
- **条件边** `add_conditional_edges(a, routing_fn, path_map=)`:`routing_fn(state)` 返回下一个节点名(分支)、节点名列表(扇出)、或 `END`。**循环**就是 routing_fn 返回上游节点名。

## 超步引擎(无状态)

引擎是一组**纯函数**,状态全在 `GraphSession`。一个**超步** = 把当前 frontier 的所有节点并发(`asyncio.gather`)跑一遍 → 合并更新 → 算下一 frontier。

- **汇合屏障**:一个节点只有当它的所有静态前驱都完成,才进 frontier(防不对称汇合提前跑)。
- **熔断**:每步前查四道闸(`max_supersteps` / `max_node_visits` / `timeout_s` / `max_total_tokens`)。

## GraphSession:可序列化快照

一次图执行的全部状态,**纯数据、零方法**:`state` / `frontier` / `superstep` / `usage` / `node_sessions`(被中断 agent 的 rein.Session)/ `sub_sessions`(子图快照)/ `pending_interrupt`。

> 暂停 = `model_dump_json()` 存它;恢复 = 喂回它。和 rein 的 `Session` 同一套心法,升一维到图。

## 图级 HITL(复用 rein 的命门)

某 `AgentNode` 因 `permission="ask"` 中断 → rein 的 `Interrupt`+`Session` 原样冒泡 → 整图暂停、存盘。`graph.resume(thread_id 或 session, approve=)` → 把恢复**分发回那个 agent 的 `agent.aresume`** → 续跑。**零新机制**。

```python
r = app.invoke({"input": "退款 100"}, thread_id="job1")   # → interrupted
# ...人批准后(可换进程)...
r = app.resume("job1", approve=True)                       # → done
```
