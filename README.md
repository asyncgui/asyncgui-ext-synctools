# Queue

An `asyncio.Queue` equivalent for asyncgui.

```python
import asyncgui as ag
from asyncgui_ext.queue import Queue

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
```

```
produced A
produced B
consumed A
produced C
consumed B
consumed C
```

## Installation

Pin the minor version.

```
poetry add asyncgui-ext-queue@~0.3
pip install "asyncgui-ext-queue>=0.3,<0.4"
```

## Tested on

- CPython 3.10
- CPython 3.11
- CPython 3.12
- CPython 3.13
- CPython 3.14
