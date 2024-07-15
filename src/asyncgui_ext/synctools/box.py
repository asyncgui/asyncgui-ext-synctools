'''
.. code-block::

    import asyncgui as ag
    from asyncgui_ext.synctools.box import Box

    async def async_fn1(box):
        for __ in range(10):
            args, kwargs = await box.get()
            assert args == (1, )
            assert kwargs == {'crow': 'raven', }

    async def async_fn2(box):
        for __ in range(10):
            args, kwargs = await box.get()
            assert args == (2, )
            assert kwargs == {'frog': 'toad', }

    box = Box()
    box.put(1, crow='raven')
    ag.start(async_fn1(box))
    box.update(2, frog='toad')
    ag.start(async_fn2(box))
'''


__all__ = ('Box', )
import types


class Box:
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
