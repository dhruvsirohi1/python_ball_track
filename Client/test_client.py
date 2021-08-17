import os
import sys
import unittest
from multiprocessing import Lock, Value, Queue
from queue import Queue

import numpy as np
import cv2 as cv
import client


class NoStdStreams(object):
    def __init__(self, stdout = None, stderr=None):
        self.devnull = open(os.devnull, 'w')
        self._stdout = stdout or self.devnull or sys.stdout
        self._stderr = stderr or self.devnull or sys.stderr

    def __enter__(self):
        self.old_stdout, self.old_stderr = sys.stdout, sys.stderr
        self.old_stdout.flush()
        self.old_stderr.flush()
        sys.stdout, sys.stderr = self._stdout, self._stderr

    def __exit__(self, exc_type, exc_value, traceback):
        self._stdout.flush()
        self._stderr.flush()
        sys.stdout = self.old_stdout
        sys.stderr = self.old_stderr
        self.devnull.close()

class TestServer(unittest.TestCase):

    def test_noCircle(self):
        img = np.zeros((400, 400, 3), dtype='uint8')
        frames = Queue()
        frames.put(img)
        est = Queue()
        lock = Lock()

        self.assertTrue(client.findCircle(frames, est, lock, True).empty(),
                          'No circles should be found on a black screen.')

    def test_detectBall(self):
        img = np.zeros((400, 400, 3), dtype='uint8')
        cv.circle(img, (100, 100), 18, (255, 0, 0), -1)
        frames = Queue()
        frames.put(img)
        est = Queue()
        lock = Lock()
        self.assertEqual(client.findCircle(frames, est, lock, True).qsize(), 1,
                        'Method findCenter() should detect one circle of nearly the same ' +
                        'size as the ball.')

if __name__ == '__main__':
    unittest.main()
