__all__ = (
    'Event',
)
import types
import typing as T


class Event:
    '''
    Similar to :class:`asyncio.Event`.
    The differences are:

    * :meth:`set` accepts any number of arguments but doesn't use them at all so it can be used as a callback function
      in any library.
    * :attr:`is_set` is a property not a function.

    .. code-block::

        e = Event()
        any_library.register_callback(e.set)
    '''

    __slots__ = ('_flag', '_waiting_tasks', )

    def __init__(self):
        self._flag = False
        self._waiting_tasks = []

    @property
    def is_set(self) -> bool:
        return self._flag

    def set(self, *args, **kwargs):
        '''
        Set the event.
        Unlike asyncio's, all tasks waiting for this event to be set will be resumed *immediately*.
        '''
        if self._flag:
            return
        self._flag = True
        tasks = self._waiting_tasks
        self._waiting_tasks = []
        for t in tasks:
            if t is not None:
                t._step()

    def clear(self):
        '''Unset the event.'''
        self._flag = False

    @types.coroutine
    def wait(self) -> T.Awaitable:
        '''
        Wait for the event to be set.
        Return *immediately* if it's already set.
        '''
        if self._flag:
            return
        try:
            tasks = self._waiting_tasks
            idx = len(tasks)
            yield tasks.append
        finally:
            tasks[idx] = None
