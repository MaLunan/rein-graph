# reinGraph

> **把多个 rein agent 编排成有状态的图工作流** —— 条件分支、循环、并行汇合、人在环路(HITL)。

[![test](https://github.com/MaLunan/rein-graph/actions/workflows/test.yml/badge.svg)](https://github.com/MaLunan/rein-graph/actions/workflows/test.yml)

reinGraph 之于 [rein](https://github.com/MaLunan/rein),如同 **LangGraph 之于 LangChain**。
但根本区别在于 ——【**内核全部复用 rein,而非重造**】:

- 图的 checkpoint 复用 rein 的 `SessionStore`;
- 图的暂停 / 恢复复用 rein 的 `aresume`(喂回状态从断点继续);
- 节点内执行复用 rein 的 `Agent.arun` / `RunResult`;
- 图级中断复用 rein 的 `Interrupt`(原样冒泡);
- 熔断照抄 rein 的 `check_circuit` 纯函数形态。

reinGraph 新增的只有「图拓扑」这一维。

## 安装

```bash
pip install rein-graph        # 装完即带 rein-agent
```

```python
import reingraph
```

## 示例

`examples/` 全部用 MockProvider,离线零成本可跑(`python examples/<name>.py`):

| 示例 | 演示 |
|---|---|
| [sequential.py](examples/sequential.py) | 顺序流水线(A → B → END) |
| [fanout.py](examples/fanout.py) | 并行扇出 + 汇合 |
| [control_flow.py](examples/control_flow.py) | 条件路由 + reflexion 循环 |
| [hitl.py](examples/hitl.py) | 图级人工审批(HITL) |
| [checkpoint.py](examples/checkpoint.py) | 存盘 → 换进程 load → 批准恢复 |
| [error_handling.py](examples/error_handling.py) | 节点异常处理 + 自动重试 |
| [streaming.py](examples/streaming.py) | astream 事件流 |
| [subgraph.py](examples/subgraph.py) | 子图(图作节点) |

## 状态

**0.2.0 Beta** —— G0–G7 全部完成(顺序 / 条件 / 循环 / 并行扇出汇合 / 图级 HITL / 流式 / 子图 / 可视化)+ 生产加固(节点异常处理 + 超时重试 + 图级结构化日志,节点失败三层防线:自动重试 → 错误中断 → 熔断)。CI 全套绿(ruff + mypy + pytest,Python 3.11–3.13)。

## 许可

Apache-2.0
