import itertools

import pytest
import asyncgui as ag
from asyncgui_ext.synctools.queue import Queue, Closed, WouldBlock

p = pytest.mark.parametrize
p_order = p('order', ('lifo', 'fifo', 'small-first'))
p_capacity = p('capacity', [1, 2, None, ])
p_capacity2 = p('capacity', [1, 2, 3, 4, None, ])
p_limited_capacity = p('capacity', [1, 2, ])


@p('capacity', (-1, 0, 0.0, 1.0, -1.0, '1', ))
def test_invalid_capacity_value(capacity):
    with pytest.raises(ValueError):
        Queue(capacity=capacity)


@p_capacity
@p_order
def test_container_type(capacity, order):
    q = Queue(capacity=capacity, order=order)
    if capacity != 1 and order == 'fifo':
        from collections import deque
        assert isinstance(q._c, deque)
    else:
        assert isinstance(q._c, list)


@p_capacity
@p('nowait', [True, False, ])
def test_put_an_item_into_a_closed_queue(capacity, nowait):
    q = Queue(capacity=capacity)
    q.close()
    with pytest.raises(Closed):
        q.put_nowait('Z') if nowait else ag.start(q.put('Z'))


@p_capacity
@p('nowait', [True, False, ])
def test_put_an_item_into_a_half_closed_queue(capacity, nowait):
    q = Queue(capacity=capacity)
    q.half_close()
    with pytest.raises(Closed):
        q.put_nowait('Z') if nowait else ag.start(q.put('Z'))


@p_capacity
@p('nowait', [True, False, ])
def test_get_an_item_from_a_closed_queue(capacity, nowait):
    q = Queue(capacity=capacity)
    q.close()
    with pytest.raises(Closed):
        q.get_nowait() if nowait else ag.start(q.get())


@p_capacity
@p('nowait', [True, False, ])
def test_get_an_item_from_a_half_closed_queue(capacity, nowait):
    q = Queue(capacity=capacity)
    q.half_close()
    with pytest.raises(Closed):
        q.get_nowait() if nowait else ag.start(q.get())


@p_capacity2
def test_put_and_get_in_the_same_task(capacity):

    async def async_fn():
        q = Queue(capacity=capacity)
        await q.put('A')
        return await q.get()

    task = ag.start(async_fn())
    assert task.result == 'A'


@p_capacity2
def test_put_and_get(capacity):
    q = Queue(capacity=capacity)
    putter = ag.start(q.put('A'))
    getter = ag.start(q.get())
    assert putter.finished
    assert getter.result == 'A'


@p_capacity2
def test_get_and_put(capacity):
    q = Queue(capacity=capacity)
    getter = ag.start(q.get())
    putter = ag.start(q.put('A'))
    assert putter.finished
    assert getter.result == 'A'


@p_capacity2
@p('close', [True, False])
def test_async_for(capacity, close):

    async def producer(q, items):
        for i in items:
            await q.put(i)

    async def consumer(q):
        return ''.join([item async for item in q])

    q = Queue(capacity=capacity)
    c = ag.start(consumer(q))
    p = ag.start(producer(q, 'ABC'))
    assert p.finished
    assert not c.finished
    q.close() if close else q.half_close()
    assert c.result == 'ABC'


@p('close', [True, False, ])
@p_capacity2
def test_close_a_queue_while_it_holding_a_getter(close, capacity):
    async def consumer(q):
        with pytest.raises(Closed):
            await q.get()

    q = Queue(capacity=capacity)
    task = ag.start(consumer(q))
    assert not task.finished
    q.close() if close else q.half_close()
    assert task.finished


@p('close', [True, False, ])
def test_close_a_queue_while_it_holding_a_putter(close):
    async def producer(q):
        with pytest.raises(Closed):
            await q.put(None)

    q = Queue(capacity=1)
    q.put_nowait(None)
    task = ag.start(producer(q))
    assert not task.finished
    q.close() if close else q.half_close()
    assert task.finished


@p_order
def test_various_statistics(order):
    q = Queue(capacity=2, order=order)
    assert q.order == order
    assert len(q) == 0
    assert q.capacity == 2
    assert q.size == 0
    assert q.is_empty
    assert not q.is_full
    ag.start(q.put(1))
    assert q.size == 1
    assert not q.is_empty
    assert not q.is_full
    ag.start(q.put(2))
    assert q.size == 2
    assert not q.is_empty
    assert q.is_full
    ag.start(q.get())
    assert q.size == 1
    assert not q.is_empty
    assert not q.is_full
    ag.start(q.get())
    assert q.size == 0
    assert q.is_empty
    assert not q.is_full


@p_order
def test_various_statistics_nowait(order):
    q = Queue(capacity=2, order=order)
    assert q.order == order
    assert len(q) == 0
    assert q.capacity == 2
    assert q.size == 0
    assert q.is_empty
    assert not q.is_full
    q.put_nowait(1)
    assert q.size == 1
    assert not q.is_empty
    assert not q.is_full
    q.put_nowait(2)
    assert q.size == 2
    assert not q.is_empty
    assert q.is_full
    q.get_nowait()
    assert q.size == 1
    assert not q.is_empty
    assert not q.is_full
    q.get_nowait()
    assert q.size == 0
    assert q.is_empty
    assert not q.is_full


@p_capacity
def test_get_nowait_while_there_are_no_items(capacity):
    q = Queue(capacity=capacity)
    with pytest.raises(WouldBlock):
        q.get_nowait()


@p('capacity', [1, 2, ])
def test_put_nowait_while_there_are_no_getters_and_full_of_items(capacity):
    q = Queue(capacity=capacity)
    for i in range(capacity):
        q._c_put(i)
    assert q.is_full
    with pytest.raises(WouldBlock):
        q.put_nowait(99)


def test_putter_triggers_half_close():
    async def producer1(q):
        await q.put('B')
        q.half_close()

    async def producer2(q):
        with pytest.raises(Closed):
            await q.put('C')

    async def consumer1(q):
        assert await q.get() == 'A'

    async def consumer2(q):
        assert await q.get() == 'B'

    q = Queue(capacity=1)
    q.put_nowait('A')
    p1 = ag.start(producer1(q))
    p2 = ag.start(producer2(q))
    c1 = ag.start(consumer1(q))
    c2 = ag.start(consumer2(q))
    assert p1.finished
    assert p2.finished
    assert c1.finished
    assert c2.finished
    assert q.is_empty


def test_putter_triggers_close():
    async def producer1(q):
        await q.put('B')
        q.close()

    async def producer2(q):
        with pytest.raises(Closed):
            await q.put('C')

    async def consumer1(q):
        assert await q.get() == 'A'

    async def consumer2(q):
        with pytest.raises(Closed):
            await q.get()

    q = Queue(capacity=1)
    q.put_nowait('A')
    p1 = ag.start(producer1(q))
    p2 = ag.start(producer2(q))
    c1 = ag.start(consumer1(q))
    c2 = ag.start(consumer2(q))
    assert p1.finished
    assert p2.finished
    assert c1.finished
    assert c2.finished


@p_capacity2
@p('close', [True, False, ])
def test_getter_triggers_close(capacity, close):
    async def producer1(q):
        await q.put('A')

    async def producer2(q):
        with pytest.raises(Closed):
            await q.put('B')

    async def consumer1(q):
        assert await q.get() == 'A'
        q.close() if close else q.half_close()

    async def consumer2(q):
        with pytest.raises(Closed):
            await q.get()

    q = Queue(capacity=capacity)
    c1 = ag.start(consumer1(q))
    c2 = ag.start(consumer2(q))
    p1 = ag.start(producer1(q))
    p2 = ag.start(producer2(q))
    assert p1.finished
    assert p2.finished
    assert c1.finished
    assert c2.finished


@p('capacity', [1, None, ])
@p("script", itertools.permutations("P2 P5 C2 C4 C1".split(), 5))
def test_various_permutations(capacity, script):
    consumed = []

    async def producer(q, n_items):
        for __ in range(n_items):
            await q.put(str(n_items))

    async def consumer(q, n_items):
        for __ in range(n_items):
            consumed.append(await q.get())

    q = Queue(capacity=capacity)
    tasks = []
    for action in script:
        if action[0] == 'P':
            tasks.append(ag.start(producer(q, int(action[1:]))))
        elif action[0] == 'C':
            tasks.append(ag.start(consumer(q, int(action[1:]))))
        else:
            pytest.fail(f"Unknown action: {action}")
    assert q.is_empty
    for t in tasks:
        assert t.finished
    consumed.sort()
    assert ''.join(consumed) == '2255555'



def test_quirk():
    '''これはテストでは無くどうしても取り除けなかった癖の確認。これが通らなくなったらドキュメントもそれに合わせて書き換えないといけない。'''
    async def async_fn1(q, consumed):
        await q.put('A')
        await q.put('B')
        item = await q.get()
        consumed.append(item)
        await q.put('C')
        item = await q.get()
        consumed.append(item)

    async def async_fn2(q, consumed):
        item = await q.get()
        consumed.append(item)

    consumed = []
    q = Queue(capacity=1)
    ag.start(async_fn1(q, consumed))
    ag.start(async_fn2(q, consumed))
    assert consumed == ['B', 'C', 'A']
