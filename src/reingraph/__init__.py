"""reinGraph —— 图编排框架:把多个 rein agent 编排成有状态的图工作流。

定位类比:reinGraph 之于 rein,如同 LangGraph 之于 LangChain。
但根本区别在于 ——【内核全部复用 rein,而非重造】:
  - 图的 checkpoint 复用 rein 的 SessionStore;
  - 图的暂停/恢复复用 rein 的 aresume(喂回状态从断点继续);
  - 节点内执行复用 rein 的 Agent.arun / RunResult;
  - 图级中断复用 rein 的 Interrupt(原样冒泡);
  - 熔断照抄 rein 的 check_circuit 纯函数形态。
reinGraph 新增的只有"图拓扑"这一维。

公开 API 随各阶段(G0-G7)模块完成逐步在此导出。
"""

__version__ = "0.1.0"
