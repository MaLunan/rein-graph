"""日志测试:enable_logging 不报错;engine 在完成/熔断处埋点(带 thread_id 作 trace)。"""

import logging

from reingraph import GraphConfig, StateGraph, enable_logging


def test_enable_logging不报错():
    enable_logging(logging.DEBUG)  # 含「尽力开 rein 日志」,不应抛异常


def test_完成有日志且带thread_id(caplog):
    async def n(sv):
        return {"out": "ok"}

    g = StateGraph()
    g.add_node("n", n)
    g.set_entry_point("n")
    g.set_finish_point("n")
    with caplog.at_level(logging.INFO, logger="reingraph"):
        g.compile().invoke({"input": "x"}, thread_id="t1")
    msgs = " ".join(r.message for r in caplog.records)
    assert "图完成" in msgs
    assert "t1" in msgs  # thread_id 作 trace


def test_熔断有日志(caplog):
    async def loop(sv):
        return {}

    g = StateGraph()
    g.add_node("loop", loop)
    g.set_entry_point("loop")
    g.add_conditional_edges("loop", lambda s: "loop")
    with caplog.at_level(logging.WARNING, logger="reingraph"):
        g.compile(config=GraphConfig(max_node_visits=3)).invoke({})
    assert any("熔断" in r.message for r in caplog.records)
