"""Test fixtures for the EventBus unit tests (Task 5).

* Resets the process-wide EventBus singleton before/after each test so a fresh
  bus can be constructed (INV-EB-001 permits exactly one instance per process;
  tests reuse the process and must reset between tests).
* Marks only the *coroutine* tests with ``pytest.mark.asyncio``. We cannot rely
  on a module-level ``pytestmark`` because some ``test_*`` functions in
  ``test_event_bus.py`` are synchronous (enums/config), and marking a sync
  function with the asyncio marker fails under pytest-asyncio strict mode. A
  collection hook scopes the marker to async functions only, so no change to
  ``pyproject.toml`` (out of Task 5 scope) is needed.
"""

import asyncio
import inspect

import pytest

from aios.events.core.bus import reset_event_bus_singleton


@pytest.fixture(autouse=True)
def _reset_event_bus_singleton():
    reset_event_bus_singleton()
    yield
    reset_event_bus_singleton()


def pytest_collection_modifyitems(items):
    """Apply the asyncio marker to coroutine test functions only."""
    for item in items:
        if "asyncio" not in item.keywords:
            func = getattr(item, "function", None)
            if func is not None and (
                inspect.iscoroutinefunction(func)
                or asyncio.iscoroutinefunction(func)
            ):
                item.add_marker(pytest.mark.asyncio)
