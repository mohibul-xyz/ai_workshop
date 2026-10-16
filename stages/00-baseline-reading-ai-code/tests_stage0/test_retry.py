"""retry.py — weak logic (no sleep, wrong backoff) + hidden bugs (mutable default, bare except)."""

import pytest


class Flaky:
    def __init__(self, failures: int, exc: type[BaseException] = ConnectionError) -> None:
        self.failures, self.exc, self.calls = failures, exc, 0

    def __call__(self) -> str:
        self.calls += 1
        if self.calls <= self.failures:
            raise self.exc("boom")
        return "ok"


def _no_sleep(mod, monkeypatch) -> list[float]:
    slept: list[float] = []
    monkeypatch.setattr(mod.time, "sleep", slept.append)
    return slept


def test_sleeps_between_attempts(load, monkeypatch) -> None:
    mod = load("retry")
    slept = _no_sleep(mod, monkeypatch)
    assert mod.retry(Flaky(2), attempts=3, base_delay=0.5) == "ok"
    assert len(slept) == 2


def test_backoff_doubles_each_time(load, monkeypatch) -> None:
    mod = load("retry")
    _no_sleep(mod, monkeypatch)
    history: list[float] = []
    mod.retry(Flaky(3), attempts=4, base_delay=0.5, history=history)
    assert history == [0.5, 1.0, 2.0]


def test_no_mutable_default_arguments(load) -> None:
    mod = load("retry")
    assert not any(isinstance(d, list | dict | set) for d in mod.retry.__defaults__ or ())


def test_errors_are_not_swallowed(load, monkeypatch) -> None:
    mod = load("retry")
    _no_sleep(mod, monkeypatch)
    with pytest.raises(ConnectionError):  # retries exhausted -> the last error is raised
        mod.retry(Flaky(5), attempts=3)
    bug = Flaky(1, ValueError)
    with pytest.raises(ValueError):  # a programming error is not "transient"
        mod.retry(bug, attempts=3)
    assert bug.calls == 1
