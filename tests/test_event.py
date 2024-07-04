import pytest


def test_wait_then_fire():
    import asyncgui as ag
    from asyncgui_ext.synctools.event import Event
    TS = ag.TaskState
    e = Event()
    t1 = ag.start(e.wait())
    t2 = ag.start(e.wait())
    assert t1.state is TS.STARTED
    assert t2.state is TS.STARTED
    e.fire(7, crow='raven')
    assert t1.result == ((7, ), {'crow': 'raven', })
    assert t2.result == ((7, ), {'crow': 'raven', })


def test_fire_then_wait_then_fire():
    import asyncgui as ag
    from asyncgui_ext.synctools.event import Event
    TS = ag.TaskState
    e = Event()
    e.fire(8, crocodile='alligator')
    t1 = ag.start(e.wait())
    t2 = ag.start(e.wait())
    assert t1.state is TS.STARTED
    assert t2.state is TS.STARTED
    e.fire(7, crow='raven')
    assert t1.result == ((7, ), {'crow': 'raven', })
    assert t2.result == ((7, ), {'crow': 'raven', })


def test_cancel():
    import asyncgui as ag
    from asyncgui_ext.synctools.event import Event
    TS = ag.TaskState

    async def async_fn(ctx, e):
        async with ag.open_cancel_scope() as scope:
            ctx['scope'] = scope
            await e.wait()
            pytest.fail()
        await ag.sleep_forever()

    ctx = {}
    e = Event()
    task = ag.start(async_fn(ctx, e))
    assert task.state is TS.STARTED
    ctx['scope'].cancel()
    assert task.state is TS.STARTED
    e.fire()
    assert task.state is TS.STARTED
    task._step()
    assert task.state is TS.FINISHED


def test_complicated_cancel():
    import asyncgui as ag
    from asyncgui_ext.synctools.event import Event
    TS = ag.TaskState

    async def async_fn_1(ctx, e):
        assert (await e.wait()) == ((7, ), {'crow': 'raven', })
        ctx['scope'].cancel()

    async def async_fn_2(ctx, e):
        async with ag.open_cancel_scope() as scope:
            ctx['scope'] = scope
            await e.wait()
            pytest.fail()
        await ag.sleep_forever()

    ctx = {}
    e = Event()
    t1 = ag.start(async_fn_1(ctx, e))
    t2 = ag.start(async_fn_2(ctx, e))
    assert e._waiting_tasks == [t1, t2, ]
    assert t2.state is TS.STARTED
    e.fire(7, crow='raven')
    assert t1.state is TS.FINISHED
    assert t2.state is TS.STARTED
    assert e._waiting_tasks == []
    t2._step()
    assert t2.result is None
