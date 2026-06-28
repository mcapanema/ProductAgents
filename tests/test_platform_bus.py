import asyncio

from productagents.platform import events as ev
from productagents.platform.bus import EventBus


async def _drain(stream):
    return [e async for e in stream]


async def test_subscriber_receives_published_events_then_close_ends_stream():
    bus = EventBus()
    stream = bus.subscribe()
    collector = asyncio.ensure_future(_drain(stream))
    await asyncio.sleep(0)  # let the subscriber register its queue

    bus.publish(ev.NodeProgress(session_id="s1", seq=0, node="market", message="a"))
    bus.publish(ev.NodeProgress(session_id="s1", seq=1, node="market", message="b"))
    bus.close()

    received = await collector
    assert [e.message for e in received] == ["a", "b"]


async def test_two_subscribers_both_receive_every_event():
    bus = EventBus()
    s1, s2 = bus.subscribe(), bus.subscribe()
    c1 = asyncio.ensure_future(_drain(s1))
    c2 = asyncio.ensure_future(_drain(s2))
    await asyncio.sleep(0)

    bus.publish(ev.NodeProgress(session_id="s1", seq=0, node="x", message="hi"))
    bus.close()

    assert len(await c1) == 1
    assert len(await c2) == 1
