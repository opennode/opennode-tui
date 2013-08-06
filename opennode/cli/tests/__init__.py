import unittest
from functools import wraps

class BaseTestCase(unittest.TestCase):

    def _setUp(self):
        pass

    def _tearDown(self):
        pass

    def setUp(self):
        self._cleanup = []
        self._setUp()

    def tearDown(self):
        for cleanupf, args, kwargs in self._cleanup:
            try:
                cleanupf(*args, **kwargs)
            except Exception:
                pass
        self._tearDown()

    def _addCleanup(self, f, *args, **kwargs):
        """ unittest2-inspired resource management """
        self._cleanup.append((f, args, kwargs))


def signal_when_called(good_to_go):
    def _signal_when_called_arg_wrapper(f):
        @wraps(f)
        def _signal_when_called_wrapper(*args, **kwargs):
            good_to_go.set()
            return f(*args, **kwargs)
        return _signal_when_called_wrapper
    return _signal_when_called_arg_wrapper
