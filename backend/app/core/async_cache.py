from __future__ import annotations

import asyncio
from collections import OrderedDict
from time import monotonic
from typing import Awaitable, Callable, Generic, TypeVar


Key = TypeVar("Key")
Value = TypeVar("Value")


class AsyncTTLCache(Generic[Key, Value]):
    def __init__(self, ttl_seconds: float, max_entries: int) -> None:
        self._ttl_seconds = ttl_seconds
        self._max_entries = max_entries
        self._values: OrderedDict[Key, tuple[float, Value]] = OrderedDict()
        self._inflight: dict[Key, asyncio.Task[Value]] = {}
        self._lock = asyncio.Lock()

    async def get_or_create(
        self, key: Key, factory: Callable[[], Awaitable[Value]]
    ) -> Value:
        now = monotonic()
        async with self._lock:
            cached = self._values.get(key)
            if cached is not None:
                expires_at, value = cached
                if expires_at > now:
                    self._values.move_to_end(key)
                    return value
                del self._values[key]

            task = self._inflight.get(key)
            if task is None:
                task = asyncio.create_task(factory())
                self._inflight[key] = task

        try:
            value = await asyncio.shield(task)
        except BaseException:
            async with self._lock:
                if self._inflight.get(key) is task:
                    del self._inflight[key]
            raise

        async with self._lock:
            if self._inflight.get(key) is task:
                del self._inflight[key]
                self._values[key] = (monotonic() + self._ttl_seconds, value)
                self._values.move_to_end(key)
                while len(self._values) > self._max_entries:
                    self._values.popitem(last=False)
        return value
