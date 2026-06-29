# reinGraph 代码讲解(大白话)

> 按「依赖自底向上」逐模块讲:它是什么、为什么这么写、**复用了 rein 的哪条机制**。
> reinGraph 之于 rein,如同 LangGraph 之于 LangChain;但内核全部复用 rein,只新增「图拓扑」一维。

---

## G0:状态与节点骨架(图编排的"名词")

全部沿用 rein 的「纯数据可序列化」心法 —— 所有状态类只有数据字段、零业务方法,永远能存盘。

### `state.py` — 图的共享状态(一块黑板)

所有节点都能读写的黑板 `GraphState`,装着 KV 数据。难点是「并行时多个节点同时写**同一个键**怎么办」——
用 **channel + reducer**(借 LangGraph):每个键声明一个合并规则:
- `last_write_wins`(默认,后写覆盖)、`append`(列表追加,扇入汇合用)、`add`(累加)、`merge_dict`(字典合并)。

**关键改造**:reducer 用「名字」(查注册表)而非函数引用存,所以整块黑板能 `model_dump_json()` 存盘 ——
这是「图能 checkpoint」的地基。合并逻辑在纯函数 `apply_updates(state, updates)` 里(数据与行为分离)。

### `config.py` — 图级刹车

`GraphConfig`,照抄 rein `LoopConfig` 的多道闸,但管的是图:超步上限 / 单节点访问上限 / 墙钟超时 / 总 token。
防图无限绕圈、扇出爆炸、成本失控。

### `result.py` — 图级中断 / 流水账

**直接复用 rein 的 `Interrupt` / `Step` / `Usage`**,只在外面包一层「是哪个节点」:
- `GraphInterrupt{node, inner: rein.Interrupt}` —— 图级 HITL 不发明新中断,就是把 agent 的中断抬到图层;
- `GraphStep{node, inner_steps: list[rein.Step], ...}` —— 整图流水账 = 各节点 step 拼接 + 标注归属。

### `nodes.py` — 节点(命门)

统一协议 `Node`:每个节点实现 `ainvoke(state) -> NodeResult`,引擎不关心种类(鸭子类型)。
- **`AgentNode`** 把一个 rein agent 包成图节点:
  - 跑它 = 调 `agent.arun(prompt)`(prompt 从 state 取);
  - 它中断了(如 `permission="ask"`)就把 rein 的 `Interrupt` + `Session` **原样冒泡**进 `NodeResult`(图级 HITL 的种子);
  - 恢复 = 调 `agent.aresume`。**一行没重造,全用 rein 的。**
- **`FunctionNode`** 包普通 async 函数做编排粘合(取数/转换,不涉及 LLM,永不中断)。

> 这就坐实核心设计:**reinGraph 的节点内部完全是 rein,图层只管「节点之间」。**
