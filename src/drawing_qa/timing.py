"""Optional scan timings. Toggle with settings.yaml ``timing.enabled`` or TBCHECK_TIMING=1.

Keep this module free of other drawing_qa imports so it is easy to delete later.
When disabled, span() is a no-op and add() returns immediately.
"""

from __future__ import annotations

import os
import time
from contextlib import contextmanager

_enabled = False
_spans: dict[str, float] = {}
_counts: dict[str, int] = {}
_order: list[str] = []


def _env_enabled() -> bool | None:
    raw = os.environ.get("TBCHECK_TIMING", "").strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    return None


def configure(enabled: bool) -> None:
    """Turn timing on or off for this process. Environment TBCHECK_TIMING wins."""
    global _enabled
    env = _env_enabled()
    _enabled = bool(enabled) if env is None else env
    reset()


def is_enabled() -> bool:
    return _enabled


def reset() -> None:
    _spans.clear()
    _counts.clear()
    _order.clear()


def add(name: str, seconds: float) -> None:
    if not _enabled:
        return
    if name not in _spans:
        _order.append(name)
        _spans[name] = 0.0
        _counts[name] = 0
    _spans[name] += seconds
    _counts[name] += 1


@contextmanager
def span(name: str):
    if not _enabled:
        yield
        return
    start = time.perf_counter()
    try:
        yield
    finally:
        add(name, time.perf_counter() - start)


def format_report() -> str:
    if not _enabled or not _order:
        return ""
    width = max(len(name) for name in _order)
    lines = [
        "Timing (set timing.enabled: false in settings.yaml, or TBCHECK_TIMING=0, to disable):",
    ]
    for name in _order:
        total = _spans[name]
        count = _counts[name]
        if count > 1:
            lines.append(
                f"  {name:<{width}}  {total:8.2f}s  ({count}x, avg {total / count:.2f}s)"
            )
        else:
            lines.append(f"  {name:<{width}}  {total:8.2f}s")
    return "\n".join(lines)
