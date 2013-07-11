import unittest

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
