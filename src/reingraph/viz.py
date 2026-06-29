"""把图导出成 mermaid 文本 —— 零依赖手写(不引 graphviz,同 rein 的极薄原则)。

生成 `graph TD` 流程图:静态边画实线 `-->`,条件边(有 path_map)画带标签虚线 `-. 标签 .->`。
粘到任何支持 mermaid 的地方(GitHub README / 文档站 / mermaid.live)即可看拓扑。
"""

from typing import Any

from reingraph.edges import END, START


def _nid(n: str) -> str:
    """把 START/END 哨兵的内部 id 映射成 mermaid 友好的显示 id。"""
    if n == START:
        return "START"
    if n == END:
        return "END"
    return n


def to_mermaid(compiled: Any) -> str:
    """生成 mermaid flowchart(graph TD)文本。"""
    lines = ["graph TD", "    START([START])", "    END([END])"]
    # 静态边:实线
    for src, targets in compiled.edges.items():
        for t in targets:
            lines.append(f"    {_nid(src)} --> {_nid(t)}")
    # 条件边:虚线(有 path_map 标注每条分支;否则注释说明运行期决定)
    for src, cond in compiled.conditional.items():
        if cond.path_map:
            for label, target in cond.path_map.items():
                lines.append(f"    {_nid(src)} -. {label} .-> {_nid(target)}")
        else:
            lines.append(f"    %% {_nid(src)}: 条件路由(目标运行期由 routing_fn 决定)")
    return "\n".join(lines)
