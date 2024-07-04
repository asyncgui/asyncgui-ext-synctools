__all__ = ('Box', )
import types


class Box:
    '''
    Similar to :class:`asyncgui.AsyncBox`, but this one can handle multiple tasks simultaneously.
    This is the closest thing to :class:`asyncio.Event` in this library.

    .. code-block::

        async def async_fn(b1, b2):
            args, kwargs = await b1.get()
            assert args == (1, )
            assert kwargs == {'crow': 'raven', }

            args, kwargs = await b2.get()
            assert args == (2, )
            assert kwargs == {'frog': 'toad', }

            args, kwargs = await b1.get()
            assert args == (1, )
            assert kwargs == {'crow': 'raven', }

        b1 = Box()
        b2 = Box()
        b1.put(1, crow='raven')
        start(async_fn(b1, b2))
        b2.put(2, frog='toad')
    '''

    __slots__ = ('_item', '_waiting_tasks', )

    def __init__(self):
        self._item = None
        self._waiting_tasks = []

    @property
    def is_empty(self) -> bool:
        return self._item is None

    def put(self, *args, **kwargs):
        '''Put an item into the box if it's empty.'''
        if self._item is None:
            self.put_or_update(*args, **kwargs)

    def update(self, *args, **kwargs):
        '''Replace the item in the box if there is one already.'''
        if self._item is not None:
            self.put_or_update(*args, **kwargs)

    def put_or_update(self, *args, **kwargs):
        self._item = (args, kwargs, )
        tasks = self._waiting_tasks
        self._waiting_tasks = []
        for t in tasks:
            if t is not None:
                t._step(*args, **kwargs)

    def clear(self):
        '''Remove the item from the box if there is one.'''
        self._item = None

    @types.coroutine
    def get(self):
        '''Get the item from the box if there is one. Otherwise, wait until it's put.'''
        if self._item is not None:
            return self._item
        tasks = self._waiting_tasks
        idx = len(tasks)
        try:
            return (yield tasks.append)
        finally:
            tasks[idx] = None
