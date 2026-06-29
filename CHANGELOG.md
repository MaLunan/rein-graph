# Changelog

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 与 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### Added
- **节点异常处理(生产加固)**:节点抛异常 → 转「错误中断」(`gather(return_exceptions=True)`,不炸整图、同超步成功节点进度保留),`resume(approve=True)` 重试该节点 / `approve=False` 放弃,错误态可序列化存盘。

### Added(G0–G7 全部完成)
- **G0 状态与节点骨架**:`GraphState` + channel/reducer(名字注册表 → 可序列化)、`GraphConfig` 熔断四道闸、`GraphInterrupt`/`GraphStep`(复用 rein)、`Node` 协议 + `AgentNode`(中断冒泡)/`FunctionNode`。
- **G1 顺序引擎**:`StateGraph` 构建器(混合 API)+ 无状态 `superstep` + `GraphSession` 快照 + `CompiledGraph`。
- **G2 条件分支 + 循环**:`add_conditional_edges` + routing_fn + 循环上限熔断(`max_node_visits`)。
- **G3 并行扇出/汇合**:汇合屏障(静态前驱)+ reducer 汇合 + 并发安全。
- **G4 图级 HITL**:中断冒泡 + 进度保留 + `GraphStore`(复用 `SessionStore`)+ `aresume` 分发回 `agent.aresume`。
- **G5 流式 + 可观测**:`astream`(`GraphEvent` 事件流)+ usage 聚合 + steps 节点归属。
- **G6 子图**:`SubGraphNode`(图作节点)+ 嵌套 HITL(`sub_sessions` 自引用快照)。
- **G7 可视化 + examples**:`to_mermaid`(零依赖)+ sequential/fanout/hitl 示例。
- 工程化:Apache-2.0、ruff + mypy + pytest CI(3.11–3.13)、依赖 `rein-agent>=0.2.0`。
