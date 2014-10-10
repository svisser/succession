import itertools
from threading import Lock
from concurrent.futures import Future, CancelledError, TimeoutError


class ClosedError(Exception):
    pass


class _Chain(object):
    """ A linked list of futures.

    Each future yields a result and the next link in the chain
    """
    def __init__(self):
        self._next = Future()

    def push(self, value):
        next_ = _Chain()
        self._next.set_result((value, next_))
        return next_

    def close(self):
        self._next.cancel()

    def wait(self, timeout=None):
        try:
            result = self._next.result(timeout)
        except CancelledError:
            raise ClosedError()
        return result

    def wait_result(self, timeout=None):
        return self.wait(timeout)[0]

    def wait_next(self, timeout=None):
        return self.wait(timeout)[1]


class _SuccessionIterator(object):
    def __init__(self, head, timeout=None):
        self._next = head
        self._timeout = timeout

    def __iter__(self):
        return self

    def __next__(self):
        try:
            result, self._next = self._next.wait(self._timeout)
            return result
        except ClosedError:
            raise StopIteration()


class Succession(object):
    def __init__(self, initial=None):
        self._lock = Lock()
        self._prelude = []
        self._head = _Chain()
        self._tail = self._head

    def iter(self, timeout=None):
        with self._lock:
            return itertools.chain(
                self._prelude, _SuccessionIterator(self._head, timeout)
            )

    def __iter__(self):
        return self.iter()

    def push(self, value):
        with self._lock:
            self._tail = self._tail.push(value)

    def close(self):
        """ Stop further writes and notify all waiting listeners
        """
        with self._lock:
            self._tail.close()

    def drop(self):
        with self._lock:
            self._head = self._tail

__all__ = ['ClosedError', 'TimeoutError', 'Succession']
