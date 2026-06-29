"""GraphState —— 图的共享状态(channel + reducer)。

设计沿用 rein.Session 的心法:【纯数据、零业务方法、永远 model_dump_json() 可往返】。

状态合并借鉴 LangGraph 的 channel + reducer,解决一个顺序图没有、但并行图必有的问题:
「多个节点在同一个超步里写【同一个状态键】时,怎么合并?」——
  - 每个状态键(channel)声明一个 reducer(合并规则);
  - reducer 用【名字】而非函数引用存(REDUCERS 注册表),这样 channels 声明本身可序列化
    (函数不可序列化)——这是「能把整张图的状态 checkpoint 下来」的关键改造。

节点的输出是「部分更新」dict `{key: delta}`;引擎用 `apply_updates` 按各键 reducer 合并回 state。
默认 reducer 是 last_write_wins(顺序图够用);并行汇合的键再显式声明 append / merge_dict
——典型的「渐进式暴露」(同 rein 的 5 行示例哲学)。
"""

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, Field

# reducer 签名:(旧值, 本次新增量) -> 合并后的新值
Reducer = Callable[[Any, Any], Any]


def _last_write_wins(old: Any, new: Any) -> Any:
    """默认规则:后写覆盖(顺序图里最常用)。"""
    return new


def _append(old: Any, new: Any) -> Any:
    """列表追加(并行扇入汇合常用:每个分支把自己的产出 append 进来)。
    new 可以是单个值,也可以是列表(列表则逐项并入)。"""
    base = list(old) if old else []
    return base + (new if isinstance(new, list) else [new])


def _add(old: Any, new: Any) -> Any:
    """数值累加(计数 / 打分汇总)。"""
    return (old or 0) + new


def _merge_dict(old: Any, new: Any) -> Any:
    """字典浅合并(多分支各写若干键)。"""
    return {**(old or {}), **(new or {})}


# 名字 -> reducer 函数的注册表。channels 里只存名字(可序列化),执行期从这里查函数。
REDUCERS: dict[str, Reducer] = {
    "last_write_wins": _last_write_wins,
    "append": _append,
    "add": _add,
    "merge_dict": _merge_dict,
}


def register_reducer(name: str, fn: Reducer) -> None:
    """注册自定义 reducer(高级用户扩展合并规则)。注册后即可在 Channel.reducer 里用这个名字。"""
    REDUCERS[name] = fn


class Channel(BaseModel):
    """一个状态通道的声明:键名 + 合并规则名 + 默认值。
    只存 reducer 的【名字】,所以整个声明可序列化。"""

    name: str
    reducer: str = "last_write_wins"  # 必须是 REDUCERS 里的名字
    default: Any = None


class GraphState(BaseModel):
    """图的共享状态:一份可序列化的 KV 快照 + 各键的通道声明。

    - values:当前各通道的值(约束为 JSON 可序列化,同 rein IR);
    - channels:通道声明(拓扑期固定,运行期不变)。
    纯数据、零业务方法 —— 合并逻辑在模块函数 apply_updates 里(数据与行为分离)。
    """

    values: dict[str, Any] = Field(default_factory=dict)
    channels: dict[str, Channel] = Field(default_factory=dict)


def apply_updates(state: GraphState, updates: dict[str, Any]) -> GraphState:
    """把一批「部分更新」按各键的 reducer 合并进 state,返回【新的】GraphState(不原地改)。

    - 已声明 channel 的键:用该 channel 的 reducer 合并(old=当前值, new=本次 delta);
    - 未声明 channel 的键:默认 last_write_wins(直接覆盖),并补一个默认 channel 声明。
    纯函数、返回新对象 —— 便于 checkpoint 与可复现(同 rein「状态全在数据里」)。
    """
    new_values = dict(state.values)
    new_channels = dict(state.channels)
    for key, delta in updates.items():
        ch = new_channels.get(key)
        reducer = REDUCERS.get(ch.reducer if ch else "last_write_wins", _last_write_wins)
        old = new_values.get(key, ch.default if ch else None)
        new_values[key] = reducer(old, delta)
        if ch is None:
            new_channels[key] = Channel(name=key)  # 未声明的键补一个默认声明
    return GraphState(values=new_values, channels=new_channels)


def make_state(
    channels: dict[str, str] | list[str] | None = None,
    initial: dict[str, Any] | None = None,
) -> GraphState:
    """便捷构造 GraphState。

    channels:
      - dict[键名, reducer名]:显式声明每个键的合并规则(并行汇合时用);
      - list[键名]:全部用默认 last_write_wins;
      - None:不预声明(运行期遇到的键自动补默认)。
    initial:初始值。
    """
    chans: dict[str, Channel] = {}
    if isinstance(channels, dict):
        chans = {k: Channel(name=k, reducer=r) for k, r in channels.items()}
    elif isinstance(channels, list):
        chans = {k: Channel(name=k) for k in channels}
    return GraphState(values=dict(initial or {}), channels=chans)
