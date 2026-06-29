# Changelog

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 与 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### Added
- **G0 状态与节点骨架**:
  - `GraphState` + channel/reducer(reducer 用名字+注册表 → 整块状态可序列化)。
  - `GraphConfig` 图级熔断四道闸(超步/节点访问/超时/token)。
  - `GraphInterrupt` / `GraphStep`:直接复用 rein 的 `Interrupt` / `Step`,只包一层"哪个节点"。
  - `Node` 协议 + `AgentNode`(包 rein.Agent,中断把 rein 的 Interrupt/Session 原样冒泡)+ `FunctionNode`。
- 工程化:Apache-2.0、ruff + mypy + pytest CI(3.11–3.13)、依赖 `rein-agent>=0.2.0`。
