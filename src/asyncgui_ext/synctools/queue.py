'''
.. versionadded:: 0.2.1

.. code::

    import asyncgui as ag
    from asyncgui_ext.synctools.queue import Queue

    async def producer(q):
        for c in "ABC":
            await q.put(c)
            print('produced', c)

    async def consumer(q):
        async for c in q:
            print('consumed', c)

    q = Queue(capacity=1)
    ag.start(producer(q))
    ag.start(consumer(q))

.. code:: text

    produced A
    produced B
    consumed A
    produced C
    consumed B
    consumed C

癖 -- Quirk --
-----------------

.. code::

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
    print(consumed)

.. code:: text

    ['B', 'C', 'A']

上記の出力を見てわかるように ``A``, ``B``, ``C`` の順でキューに入れたのに
``consumed`` には ``B``, ``C``, ``A`` の順で入っています。
このような事が起こるのは ``asyncgui`` が自身ではメインループを持たない故にタイマー機能を提供できない事に起因します。
なので外部のタイマー機能を利用する事でこの問題を解消する選択肢を用意する予定なのですが、それまではこういうものだと諦めてください。
因みに ``Kivy`` を使っているのであれば ``Kivy`` のタイマー機能を用いる事でこの問題を解決済みの ``asynckivy-ext-queue``
というモジュールが既にあるので氣になる人はそちらをご利用ください。
'''

__all__ = (
    'QueueException', 'WouldBlock', 'Closed',
    'Queue', 'Order', 'QueueState',
    )
import typing as T
import enum
import heapq
from functools import partial
from collections import deque

from asyncgui import ExclusiveEvent


class QueueState(enum.Enum):
    '''
    Enum class that represents the state of the Queue.
    '''

    OPENED = enum.auto()
    '''
    All operations are allowed. 

    :meta hide-value:
    '''

    HALF_CLOSED = enum.auto()
    '''
    Putting an item into the queue is not allowed.

    :meta hide-value:
    '''

    CLOSED = enum.auto()
    '''
    Putting an item into the queue is not allowed.
    Getting an item from the queue is not allowed.

    :meta hide-value:
    '''


class QueueException(Exception):
    '''Base class of all the queue-related exceptions.'''


class WouldBlock(QueueException):
    '''Raised by X_nowait functions if X would block.'''


class Closed(QueueException):
    '''
    Occurs when:

    * one tries to get an item from a queue that is in the ``CLOSED`` state.
    * one tries to get an item from an **empty** queue that is in the ``HALF_CLOSED`` state.
    * one tries to put an item into a queue that is in the ``CLOSED`` or ``HALF_CLOSED`` state.
    '''


Item: T.TypeAlias = T.Any
Order = T.Literal['fifo', 'lifo', 'small-first']


class Queue:
    '''
    :param capacity: Cannot be zero. Unlimited if None.
    '''
    def __init__(self, *, capacity: int | None=None, order: Order='fifo'):
        if capacity is None:
            pass
        elif (not isinstance(capacity, int)) or capacity < 1:
            raise ValueError(f"'capacity' must be either a positive integer or None. (was {capacity!r})")
        self._init_container(capacity, order)
        self._state = QueueState.OPENED
        self._putters = deque[tuple[ExclusiveEvent, Item]]()
        self._getters = deque[ExclusiveEvent]()
        self._capacity = capacity
        self._order = order
        self._is_transferring = False

    def _init_container(self, capacity, order):
        # If the capacity is 1, there is no point in reordering items.
        # Therefore, for performance reasons, treat the order as 'lifo'.
        if capacity == 1 or order == 'lifo':
            c = []
            c_get = c.pop
            c_put = c.append
        elif order == 'fifo':
            c = deque(maxlen=capacity)
            c_get = c.popleft
            c_put = c.append
        elif order == 'small-first':
            c = []
            c_get = partial(heapq.heappop, c)
            c_put = partial(heapq.heappush, c)
        else:
            raise ValueError(f"'order' must be one of 'lifo', 'fifo' or 'small-first'. (was {order!r})")
        self._c = c
        self._c_get = c_get
        self._c_put = c_put

    def __len__(self) -> int:
        return len(self._c)

    size = property(__len__)
    '''Number of items in the queue. This equals to ``len(queue)``. '''

    @property
    def capacity(self) -> int | None:
        '''Number of items allowed in the queue. None if unbounded.'''
        return self._capacity

    @property
    def is_empty(self) -> bool:
        return not self._c

    @property
    def is_full(self) -> bool:
        return len(self._c) == self._capacity

    @property
    def order(self) -> Order:
        return self._order

    async def get(self) -> T.Awaitable[Item]:
        '''
        .. code-block::

            item = await queue.get()
        '''
        if self._state is QueueState.CLOSED:
            raise Closed
        if self._state is QueueState.HALF_CLOSED and self.is_empty:
            raise Closed

        if self._is_transferring or self.is_empty:
            event = ExclusiveEvent()
            self._getters.append(event)
            exc, item = (await event.wait())[0]
            if exc is not None:
                raise exc
            return item

        item = self._c_get()
        if self._putters:
            self._transfer_items()
        return item

    def get_nowait(self) -> Item:
        '''
        .. code-block::

            item = queue.get_nowait()
        '''
        if self._state is QueueState.CLOSED:
            raise Closed
        if self.is_empty:
            if self._state is QueueState.HALF_CLOSED:
                raise Closed
            raise WouldBlock

        item = self._c_get()
        if (not self._is_transferring) and self._putters:
            self._transfer_items()
        return item

    async def put(self, item) -> T.Awaitable:
        '''
        .. code-block::

            await queue.put(item)
        '''
        if self._state is not QueueState.OPENED:
            raise Closed

        if self._is_transferring or self.is_full:
            event = ExclusiveEvent()
            self._putters.append((event, item, ))
            exc = (await event.wait())[0][0]
            if exc is not None:
                raise exc
            return

        self._c_put(item)
        if self._getters:
            self._transfer_items()

    def put_nowait(self, item):
        '''
        .. code-block::

            queue.put_nowait(item)
        '''
        if self._state is not QueueState.OPENED:
            raise Closed
        if self.is_full:
            raise WouldBlock

        self._c_put(item)
        if (not self._is_transferring) and self._getters:
            self._transfer_items()

    def half_close(self):
        '''
        Partially closes the queue.
        Putting an item into it is no longer allowed.
        '''
        if self._state is not QueueState.OPENED:
            return
        self._state = QueueState.HALF_CLOSED

        Closed_ = Closed
        for putter, __ in self._putters:
            putter.fire(Closed_)
        if not self.is_empty:
            return
        for getter in self._getters:
            getter.fire(Closed_, None)

    def close(self):
        '''
        Fully closes the queue.
        Putting an item into it is no longer allowed.
        Getting an item from it is no longer allowed.
        All the items it holds will be discarded.
        '''
        if self._state is QueueState.CLOSED:
            return
        self._state = QueueState.CLOSED
        self._c.clear()

        Closed_ = Closed
        for putter, __ in self._putters:
            putter.fire(Closed_)
        for getter in self._getters:
            getter.fire(Closed_, None)

    async def __aiter__(self):
        '''
        Repeats getting an item from the queue until it gets closed.

        .. code-block::

            async for item in queue:
                ...

        This is equivalent to:

        .. code-block::

            try:
                while True:
                    item = await queue.get()
                    ...
            except Closed:
                pass
        '''
        try:
            while True:
                yield await self.get()
        except Closed:
            pass

    def _transfer_items(self):
        assert not self._is_transferring
        self._is_transferring = True
        try:
            # LOAD_FAST
            c_put = self._c_put
            c_get = self._c_get
            putters = self._putters
            getters = self._getters
            next_putter = putters.popleft
            next_getter = getters.popleft

            while True:
                while (not self.is_full) and putters:
                    putter, item = next_putter()
                    if (cb := putter._callback) is not None:
                        c_put(item)
                        cb(None)
                if (not getters) or self.is_empty:
                    break
                while (not self.is_empty) and getters:
                    getter = next_getter()
                    if (cb := getter._callback) is not None:
                        cb(None, c_get())
                if (not putters) or self.is_full:
                    break
        finally:
            self._is_transferring = False
