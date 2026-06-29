# reinGraph

> **把多个 rein agent 编排成有状态的图工作流** —— 条件分支、循环、并行汇合、人在环路(HITL)。

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

## 状态

**G0–G7 全部完成 ✅**:顺序 / 条件 / 循环 / 并行扇出汇合 / 图级 HITL(可恢复)/ 流式 / 子图嵌套 / 可视化。CI 全套绿(ruff + mypy + pytest,Python 3.11–3.13)。

## 许可

Apache-2.0
