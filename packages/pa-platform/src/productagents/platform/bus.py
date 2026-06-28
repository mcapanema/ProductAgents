"""In-process async pub/sub. One queue per subscriber.

ponytail: asyncio.Queue fan-out, single process, no broker. The IPC transport
(Phase 6) becomes just another subscriber; the broker question only arrives when
a second OS process subscribes.
"""

import asyncio
from collections.abc import AsyncIterator

from productagents.platform.events import Event


class EventBus:
    def __init__(self) -> None:
        self._subscribers: list[asyncio.Queue[Event | None]] = []
        self._closed = False

    def publish(self, event: Event) -> None:
        for queue in self._subscribers:
            queue.put_nowait(event)

    def close(self) -> None:
        self._closed = True
        for queue in self._subscribers:
            queue.put_nowait(None)  # sentinel: end of stream

    def subscribe(self) -> AsyncIterator[Event]:
        queue: asyncio.Queue[Event | None] = asyncio.Queue()
        self._subscribers.append(queue)
        if self._closed:
            queue.put_nowait(None)
        return self._consume(queue)

    async def _consume(
        self, queue: asyncio.Queue[Event | None]
    ) -> AsyncIterator[Event]:
        try:
            while True:
                event = await queue.get()
                if event is None:
                    return
                yield event
        finally:
            self._subscribers.remove(queue)
