# 子图

把一个编译好的图当作另一个图的节点 —— 嵌套复用。

```python
from reingraph import StateGraph

# 子图:一个完整的审稿流程
review = StateGraph()
review.add_node("draft", draft_agent)
review.add_node("edit", edit_agent)
review.set_entry_point("draft")
review.add_edge("draft", "edit")
review.set_finish_point("edit")
review_app = review.compile()

# 父图:把子图当一个节点
main = StateGraph()
main.add_node("research", research_agent)
main.add_node("review", review_app)        # ← 子图作节点
main.set_entry_point("research")
main.add_edge("research", "review")
main.set_finish_point("review")

r = main.compile().invoke({"input": "选题"})
```

- `add_node` 传一个 `CompiledGraph` → 自动包成 `SubGraphNode`;
- 子图跑完,它的最终 `values` 写回父 state(或用 `output_key=` 收到某个键)。

## 嵌套 HITL

子图内部某 agent 中断,会**一路冒泡到父图**:父图存盘时把子图的 `GraphSession` 也嵌进去(`sub_sessions` 自引用字段),`resume` 时一层层分发回去 ——

```
父图 resume(approve=) → 子图 aresume → agent aresume
```

同一套「可序列化快照 + 喂回」心法,只是多了一层嵌套。整个父快照(嵌着子图快照、子图快照里又嵌着 agent 的 rein.Session)一句 `model_dump_json` 全存下来。
