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

---

## G1:顺序引擎闭环(让图跑起来)

G1 把 G0 的"名词"连成能跑的图。5 个模块:

### `edges.py` — 边
`START`/`END` 两个哨兵 + 静态有向边。`add_edge(START, x)` 设入口,`add_edge(x, END)` 设出口。

### `session.py` — 图执行快照(GraphSession)+ 结果(GraphResult)
`GraphSession` 是一次图执行的全部状态:当前黑板、待跑的节点(frontier)、超步数、累计用量,以及**命门 `node_sessions`**(被中断 agent 的 rein.Session 整个嵌进来)。一句 `model_dump_json` 就能把整张图存盘。

### `engine.py` — 无状态单步引擎(照抄 rein loop.py)
`superstep` 推进一个超步:把 frontier 的节点用 `gather` 跑一遍,合并各自的更新,算出下一批要跑的节点。`arun_graph` 驱动这个循环,每步前查熔断四道闸。**引擎不存任何状态 —— 状态全在 GraphSession**,所以"暂停=存 session、恢复=喂回 session"(为 G4 留好形状)。frontier 按"全员并发"写,G3 的并行天然复用同一套。

### `graph.py` — StateGraph 构建器(混合 API)
LangGraph 熟悉的 `add_node/add_edge/set_entry_point` + rein 的 `@graph.node` 装饰器糖。`add_node` 智能适配:传 rein Agent 自动包成 AgentNode,传函数包成 FunctionNode。`compile()` 编译期校验(没入口 / 边端点不存在就立即报错)。

### `compiled.py` — CompiledGraph(可执行图)
`invoke`(同步)/ `ainvoke`(异步)从入口跑到 END。同步门面照抄 rein:在事件循环里就报错引导用 `ainvoke`(不嵌套 event loop)。

> **G1 成果**:`A→B→END` 流水线跑通,数据在节点间真流转,到 END 自动停,整图可序列化,熔断生效 —— reinGraph 现在能把 rein agent 编排成顺序工作流了。

---

## G2:条件分支 + 循环(让图会拐弯)

让图能"看状态决定下一步"。

### 条件边(`edges.py` + `graph.py` + `engine.py`)
`add_conditional_edges(source, routing_fn)`:节点跑完后,引擎调 `routing_fn(state)` 得到下一个去向(节点名 / 列表 / END),而不是走固定静态边。routing_fn 是函数、不可序列化,按 source 登记在运行期注册表(同 rein 钩子不进序列化)。引擎的 `_next_targets` 升级:有条件边就调 routing_fn,否则走静态边 —— **顺序图(G1)一行没改照样跑**。

### 循环
循环不是新机制,就是 routing_fn 返回**上游节点名**(回到自己或前面),引擎把它加回 frontier。reflexion(生成→评估→不满意回去重生成)就这么表达。

### 防失控
`max_node_visits`(单节点访问上限)+ `max_supersteps`(总超步上限)双闸兜底 —— 熔断纯函数 G1 已备好,G2 直接生效。

> **G2 成果**:图能条件分支、能带上限循环。配合 G1,reinGraph 已能表达"路由 + 反思"这类动态工作流。

---

## G3:并行扇出/汇合(map-reduce 式多 agent 协作)

让一个节点扇出到多个 agent **并发**跑,再**汇合**结果。

### 扇出
一个节点多条出边(或 routing_fn 返回列表)→ 下游多节点进 frontier → 引擎本来就用 `asyncio.gather` 并发跑(G1 就备好的形状,这里零改动)。

### 汇合屏障(`engine.py` + `compiled.py`)
编译期算每个节点的**静态前驱集合** `preds`。引擎合并改两段:**先全部跑完/记 completed,再算下一 frontier** —— 一个节点只有当它的**所有静态前驱都 completed** 才进 frontier。这样不对称汇合(d 等 b 和 e,而 e 比 b 多一跳)时,d 不会提前抢跑、读到不完整状态。

### 结果汇合
多分支写**同一个 state 键**,用 G0 的 reducer(`append`/`merge_dict`)正确并起来 —— 这正是 channel/reducer 当初存在的理由。

### 并发安全
同一个 CompiledGraph 并发跑 100 个独立请求**不串台**:CompiledGraph 只读(nodes/edges/preds),每次 ainvoke 新建独立 GraphSession —— 天然继承 rein 的"无状态蓝图"并发安全(同 rein 的 test_concurrency)。

> **G3 成果**:map-reduce 式多 agent 并发协作。reinGraph 现在能扇出 / 汇合 / 并行。

---

## G4:图级 HITL(核心卖点 —— 复用 rein 的命门)

让图能在某个 agent 节点"暂停等人审批",存盘后换进程也能恢复。

### 中断冒泡(G0 已备)+ 进度保留(`engine.py`)
某 AgentNode 因 `permission="ask"` 中断 → rein 的 `Interrupt` + `Session` 原样冒泡 → superstep 把它存进 `node_sessions`、整图暂停。同超步**已成功的兄弟节点照常合并**(进度不丢)。

### 存盘(`store.py`)
`GraphStore` 复用 rein `SessionStore` 的 save/load 形态,存的就是 `GraphSession.model_dump_json()` —— 里面**嵌着被中断 agent 的 rein.Session**。Memory/File 两个实现镜像 rein。

### 恢复(`aresume_graph`)
`graph.resume(thread_id 或 session, approve=)` → 找到中断节点 → 调它的 `agent.aresume(node_sessions[node])` —— **直接复用 rein 的恢复**。完成则推进图、再中断则多轮审批、拒绝则错误回填让 agent 自愈。

> **G4 成果**:整图(含 agent 会话)一句话存盘、换进程 resume。这是 reinGraph 区别于 LangGraph 的根本 —— **HITL / checkpoint 没写一行新机制,全是把 rein 的单 agent 中断恢复"分发到图层"**。
