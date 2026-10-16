"""Retry helper — reference fix.

Fixes: actually sleeps; delay = base * 2**attempt; no mutable default; only retryable
exceptions are caught; the last error is re-raised instead of returning None.
"""

import time
from collections.abc import Callable
from typing import Any

RETRYABLE = (ConnectionError, TimeoutError)


def retry(
    func: Callable[[], Any],
    attempts: int = 3,
    base_delay: float = 0.5,
    history: list[float] | None = None,
    retry_on: tuple[type[BaseException], ...] = RETRYABLE,
) -> Any:
    for attempt in range(attempts):
        try:
            return func()
        except retry_on:
            if attempt == attempts - 1:
                raise
            delay = base_delay * 2**attempt
            if history is not None:
                history.append(delay)
            time.sleep(delay)
    raise ValueError("attempts must be >= 1")
