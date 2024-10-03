'''
.. versionadded:: 0.2.1


'''

__all__ = (
    'Value',
)
import typing as T
from functools import partial
from collections import deque

from asyncgui import ExclusiveEvent


class RecursionError(Exception):
    pass


class Subscriber:
    __slots__ = ('callback', '_cancelled', )
    def __init__(self, callback):
        self.callback = callback
        self._cancelled = False

    def cancel(self):
        self._cancelled = True


class Value:
    def __init__(self, initial_value):
        self._value = initial_value
        self._is_notifying = False
        self._onetime_subscribers = []
        self._callbacks = []

    def set(self, new_value):
        old_value = self._value
        if new_value == old_value:
            return
        self._value = new_value
        self._notify_change(old_value, new_value)

    def get(self):
        return self._value

    value = property(get, set)

    def _notify_change(self, old_value, new_value):
        if self._is_notifying:
            raise RecursionError('Cannot change value while notifying changes')
        self._is_notifying = True
        subs = self._onetime_subscribers
        self._onetime_subscribers = []

        try:
            for callback in self._callbacks:
                callback(old_value, new_value)
            for sub in subs:
                if sub._cancelled:
                    continue
                sub.callback(old_value, new_value)
        finally:
            self._is_notifying = False


