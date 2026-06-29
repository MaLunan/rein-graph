# 设计哲学:复用 rein,而非重造

reinGraph 与 LangGraph 最本质的区别:**LangGraph 自己造了 checkpoint / 状态机 / 中断恢复(因为 LangChain 没有);reinGraph 把这三样直接「借」自 rein**。

| 能力 | LangGraph 自己造 | reinGraph 复用 rein 的 |
|---|---|---|
| 执行单元 | 自定义 Runnable | `rein.Agent` + `RunResult` |
| 可序列化快照 | 自定义 Checkpoint | rein 的 pydantic 纯数据 + 内嵌 `Session` |
| 无状态单步推进 | Pregel 超步引擎 | rein 的 `step()` 心法 |
| 持久化 | 自定义 Checkpointer | `rein.SessionStore` Protocol |
| HITL 中断 / 恢复 | 自定义 interrupt / Command | `rein.Interrupt` + `aresume`(原样冒泡 + 分发) |
| 熔断 | recursion_limit | rein 四道闸 + `check_circuit` 纯函数 |
| 可观测 | 自定义 stream mode | `RunResult.usage` / `.steps` 聚合 |
| 离线测试 | LangSmith mock | `rein.MockProvider`(核心自带) |

## 设计铁律(从 rein 原样继承)

1. **数据与行为分离**:所有 `*State` / `*Session` 只有数据字段、零业务方法,永远可 `model_dump_json()`。
2. **引擎无状态**:状态全在 `GraphSession`,暂停 = 存盘、恢复 = 喂回。
3. **为恢复留形状**:每个抽象先把「恢复需要的信息」收进可序列化结构。
4. **极薄优先**:能不进核心走 extras;mermaid 零依赖手写,不引 graphviz。

## 一句话

> reinGraph 新增的**只有「图拓扑」这一维**(节点、边、超步引擎、汇合屏障、路由、可视化)。节点内部、快照、单步推进、中断恢复、持久化、熔断、用量、离线测试 —— 八样全是 rein 的机制原样复用或同构升维。这正是「LangGraph 之于 LangChain」应有的姿态:**图引擎只编排,不重造内核**。

(逐模块的实现讲解见仓库内 `docs/code-guide.md`。)
