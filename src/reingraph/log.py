"""结构化日志 —— 复用 rein 的日志心法。

默认安静(NullHandler,库的最佳实践);`enable_logging()` 一行开启 reinGraph 日志,
并尽力同时开底层 rein 的日志(让节点内 agent 的日志一起出来)。

engine 在熔断 / 中断 / 完成处埋点,每条带 `thread_id` 作 trace —— 只记节点名 / 超步 / 原因,
【不记 state / prompt / 输出】(脱敏,同 rein 的原则)。
"""

import logging
import sys

logger = logging.getLogger("reingraph")
logger.addHandler(logging.NullHandler())  # 默认安静:不配 handler 就不输出


def enable_logging(level: int = logging.INFO, *, stream=sys.stderr) -> None:
    """开启 reinGraph 日志输出(默认 INFO 到 stderr),并尽力同时开底层 rein 的日志。"""
    handler = logging.StreamHandler(stream)
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] reingraph: %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    try:
        from rein import enable_logging as _rein_enable  # 让节点内 agent 的日志也出来

        _rein_enable(level=level)
    except Exception:
        pass  # rein 日志开不了不影响 reinGraph 自身日志
