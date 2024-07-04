__all__ = ('Event', )
import types


class Event:
    '''
    Similar to :class:`asyncgui.AsyncEvent`, but this one can handle multiple tasks simultaneously.

    .. code-block::

        async def async_fn(e):
            args, kwargs = await e.wait()
            assert args == (2, )
            assert kwargs == {'crow': 'raven', }

            args, kwargs = await e.wait()
            assert args == (3, )
            assert kwargs == {'toad': 'frog', }

        e = Event()
        e.fire(1, crocodile='alligator')
        start(async_fn(e))
        e.fire(2, crow='raven')
        e.fire(3, toad='frog')
    '''

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
