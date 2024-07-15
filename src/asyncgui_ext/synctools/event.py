'''
.. code-block::

    import asyncgui as ag
    from asyncgui_ext.synctools.event import Event

    async def async_fn1(e):
        args, kwargs = await e.wait()
        assert args == (1, )
        assert kwargs == {'crow': 'raven', }

        args, kwargs = await e.wait()
        assert args == (2, )
        assert kwargs == {'toad': 'frog', }

    async def async_fn2(e):
        args, kwargs = await e.wait()
        assert args == (2, )
        assert kwargs == {'toad': 'frog', }

    e = Event()
    ag.start(async_fn1(e))
    e.fire(1, crow='raven')
    ag.start(async_fn2(e))
    e.fire(2, toad='frog')
'''

__all__ = ('Event', )
import types


class Event:
    __slots__ = ('_waiting_tasks', )

    def __init__(self):
        self._waiting_tasks = []

    def fire(self, *args, **kwargs):
        tasks = self._waiting_tasks
        self._waiting_tasks = []
        for t in tasks:
            if t is not None:
                t._step(*args, **kwargs)

    @types.coroutine
    def wait(self):
        tasks = self._waiting_tasks
        idx = len(tasks)
        try:
            return (yield tasks.append)
        finally:
            tasks[idx] = None
