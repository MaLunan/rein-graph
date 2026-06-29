"""GraphStore —— 图执行快照(GraphSession)的持久化。

【复用 rein.SessionStore 的形态】:同样的 save / load Protocol,存的是 GraphSession.model_dump_json()。
存哪、怎么存(redis / db)是用户的事 —— 框架对数据库零依赖零绑定(同 rein)。
MemoryGraphStore / FileGraphStore 镜像 rein 的 MemorySessionStore / FileSessionStore。
"""

from pathlib import Path
from typing import Protocol, runtime_checkable

from reingraph.session import GraphSession


@runtime_checkable
class GraphStore(Protocol):
    """图快照持久化接口(与 rein.SessionStore 同构)。"""

    def save(self, thread_id: str, gs: GraphSession) -> None: ...

    def load(self, thread_id: str) -> GraphSession | None: ...


class MemoryGraphStore:
    """内存版:进程内 dict,测试 / 单机用。"""

    def __init__(self) -> None:
        self._data: dict[str, str] = {}

    def save(self, thread_id: str, gs: GraphSession) -> None:
        self._data[thread_id] = gs.model_dump_json()  # 存 JSON 串(含嵌套的 rein.Session)

    def load(self, thread_id: str) -> GraphSession | None:
        raw = self._data.get(thread_id)
        return GraphSession.model_validate_json(raw) if raw is not None else None


class FileGraphStore:
    """文件版:每个 thread_id 一个 .json 文件。"""

    def __init__(self, directory: str = ".rein_graph_sessions") -> None:
        self.dir = Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)

    def _path(self, thread_id: str) -> Path:
        safe = thread_id.replace("/", "_").replace("..", "_")  # 防路径穿越(同 rein)
        return self.dir / f"{safe}.json"

    def save(self, thread_id: str, gs: GraphSession) -> None:
        self._path(thread_id).write_text(gs.model_dump_json(), encoding="utf-8")

    def load(self, thread_id: str) -> GraphSession | None:
        p = self._path(thread_id)
        return (
            GraphSession.model_validate_json(p.read_text(encoding="utf-8")) if p.exists() else None
        )
