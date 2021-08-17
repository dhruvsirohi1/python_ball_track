import sys
import os
import unittest
from multiprocessing import Lock, Value, Queue
from queue import Queue

import numpy as np

from Server import server


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
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_CreateBall(self):
        ball = server.BouncingBall(50, 50, 2)
        self.assertIsNotNone(ball, 'Ball was not created.')

    def test_moveBall(self):
        ball = server.BouncingBall(50, 50, 2)
        initial_pos = ball.getPos()
        ball.updatePos()
        final_pos = ball.getPos()
        self.assertFalse((initial_pos == final_pos).all(), 'Ball did not move.')

    def test_ballSpeed(self):
        with NoStdStreams():
            self.assertRaises(ValueError, server.BouncingBall, 50, 50, 30)

    def test_errorEstimate(self):
        actual_pos = Queue()
        est_pos = Queue()
        p1 = np.array((1, 1), dtype='uint8')
        p2 = np.array((3, 9), dtype='uint8')
        p3 = np.array((10, 1), dtype='uint8')

        actual_pos.put(p1)
        est_pos.put(p1)

        actual_pos.put(p2)
        est_pos.put(p2)

        actual_pos.put(p3)
        est_pos.put(p3)

        err = Value('d')
        err.value = 0
        connection = Value('i')
        connection.value = 1
        graphics = Value('i')
        graphics.value = -1
        toterr = server.calculateError(err, actual_pos, est_pos, Lock(), connection, graphics, test=True)
        with NoStdStreams():
            self.assertEqual(0, toterr, 'Total Error should be zero for identical lists of coordinates.')


# def calculateError(total_error, actual_centers, received_centers, lock, connection):


if __name__ == '__main__':
    unittest.main()
