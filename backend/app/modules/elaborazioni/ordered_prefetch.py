from __future__ import annotations

import asyncio
from collections import deque
from itertools import cycle


class OrderedPrefetch:
    def __init__(self, items, resources, fetch) -> None:
        if not resources:
            raise ValueError("At least one resource is required")
        self._items = iter(items)
        self._resources = cycle(resources)
        self._fetch = fetch
        self._pending = deque()
        for _ in resources:
            self._submit_next()

    def _submit_next(self) -> None:
        try:
            item = next(self._items)
        except StopIteration:
            return
        self._pending.append(asyncio.create_task(self._fetch(item, next(self._resources))))

    async def take(self):
        task = self._pending.popleft()
        try:
            return await task
        finally:
            self._submit_next()

    async def close(self) -> None:
        for task in self._pending:
            task.cancel()
        await asyncio.gather(*self._pending, return_exceptions=True)
        self._pending.clear()
