"""真实厂商冒烟:用真实 agent 跑一张图。默认 skip —— 需 REIN_SMOKE=1 + 对应厂商 key + 装 litellm。

开启:
    pip install rein-graph "rein-agent[litellm]"
    export DEEPSEEK_API_KEY=...        # 或 ANTHROPIC_API_KEY / OPENAI_API_KEY
    export REIN_SMOKE=1
    pytest tests/test_smoke.py -v

设计同 rein:这些测试会真的花钱、需要网络,所以默认 skip,绝不混进日常 pytest(必须 0 成本、可离线)。
"""

import os

import pytest

pytestmark = pytest.mark.skipif(
    not os.getenv("REIN_SMOKE"),
    reason="真实冒烟:需 REIN_SMOKE=1 + 厂商 key + 装好 litellm 才跑",
)


def _model() -> str:
    return os.getenv("REIN_SMOKE_MODEL", "deepseek/deepseek-chat")


def _have_key() -> bool:
    return bool(
        os.getenv("DEEPSEEK_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or os.getenv("ANTHROPIC_API_KEY")
    )


def test_smoke_顺序图():
    pytest.importorskip("litellm")
    if not _have_key():
        pytest.skip("缺厂商 key")
    from rein import Agent

    from reingraph import StateGraph

    g = StateGraph()
    g.add_node("plan", Agent(_model(), system="用一句话给主题列个大纲"))
    g.add_node("write", Agent(_model(), system="根据上文,写一句话"))
    g.set_entry_point("plan")
    g.add_edge("plan", "write")
    g.set_finish_point("write")
    r = g.compile().invoke({"input": "缰绳"})
    assert r.status == "done" and r.values["output"]
    assert r.usage.input_tokens > 0  # 真实用量被聚合


def test_smoke_条件路由():
    pytest.importorskip("litellm")
    if not _have_key():
        pytest.skip("缺厂商 key")
    from rein import Agent

    from reingraph import StateGraph
    from reingraph.edges import END

    g = StateGraph()
    g.add_node("triage", Agent(_model(), system="只回答一个字母:A 或 B"))
    g.add_node("a", Agent(_model(), system="说一句话"))
    g.add_node("b", Agent(_model(), system="说一句话"))
    g.set_entry_point("triage")
    g.add_conditional_edges("triage", lambda s: "a" if "A" in (s.get("output") or "") else "b")
    g.add_edge("a", END)
    g.add_edge("b", END)
    r = g.compile().invoke({"input": "请回答 A"})
    assert r.status == "done"
