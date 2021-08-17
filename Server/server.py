# Simple server that is used to calibrate
# client modules.
# Creates a bouncing ball animation using
# OpenCV, sends recorded frames to clients
# for processing. 
# Receives client calculation(center of ball) and calculates error between 
# the calculation and result.
#
# Author: Dhruv Sirohi

import asyncio
import os
import numpy as np
import cv2 as cv
import pickle
import sys
import keyboard
import time
from aiortc import RTCPeerConnection, MediaStreamTrack, RTCSessionDescription, RTCIceCandidate
from aiortc.contrib.media import MediaRelay
from aiortc.contrib.signaling import TcpSocketSignaling, BYE
from aiortc.mediastreams import MediaStreamError
from numpy import random
from multiprocessing import Process, Queue, Value, Lock

HOST = '127.0.0.1'
OUT_PORT = 8080

TEXT_FONT = cv.FONT_HERSHEY_SIMPLEX
FONT_SCALE = 1
FONT_COLOR = (255, 255, 255)
LINE_TYPE = 2
relay = MediaRelay()

COLORS = {
    "blue": (255, 0, 0),
    "green": (0, 128, 0),
    "red": (0, 0, 255)
}

#######################################################################################################################


class BouncingBall:
    """
    Class for handling continuous 2D image of ball bouncing
    across the screen.

    Stores the center and the current frame which may be used for
    display if server chooses to do so.

    Ball speed update after collision with edges has been randomized.
    i.e. the elasticity is unpredictable.
    """

    BALL_RADIUS = 20
    CANVAS_HEIGHT = 400
    CANVAS_WIDTH = 400
    kind = "frame"

    def __init__(self, xpos=100, ypos=100, speed=1):
        self.window = None
        self.x = xpos
        self.y = ypos
        if speed > 10:
            print('Ball speed too high for acceptable frame rate.')
            raise ValueError
        self.dx = self.dy = speed
        self.canvas = np.zeros((self.CANVAS_HEIGHT, self.CANVAS_WIDTH, 3), dtype='uint8')
        self.frame = cv.circle(self.canvas, (self.x, self.y), self.BALL_RADIUS, (255, 0, 0), -1)

    def updatePos(self):
        '''
        Update the position of the ball.
        :return: None
        '''
        # print('updating')
        if (self.x + self.BALL_RADIUS >= self.CANVAS_HEIGHT or
                self.x - self.BALL_RADIUS <= 0):

            self.dx = -1 * random.randint(1, 5) * np.sign(self.dx)

        if (self.y + self.BALL_RADIUS >= self.CANVAS_WIDTH or
                self.y - self.BALL_RADIUS <= 0):

            self.dy = -1 * random.randint(1, 5) * np.sign(self.dy)

        self.x = self.x + self.dx
        self.y = self.y + self.dy
        self.canvas = np.zeros((self.CANVAS_HEIGHT, self.CANVAS_WIDTH, 3), dtype='uint8')
        self.frame = cv.circle(self.canvas, (self.x, self.y), self.BALL_RADIUS, COLORS["blue"], -1)

    def getFrame(self):
        '''
        Returnt the current frame.
        :return: np.array (2D)
        '''
        return self.frame

    def updateSpeed(self, speed=1):
        self.dx = self.dy = speed

    def updateXspeed(self, xspeed=1):
        self.dx = xspeed

    def updateYspeed(self, yspeed=1):
        self.dy = yspeed

    def getPos(self):
        return np.array((self.x, self.y))

    def getXpos(self):
        return self.x

    def getYpos(self):
        return self.y

#######################################################################################################################

# class BallFrameTrack(MediaStreamTrack):
#
#     kind = "video"
#
#     def __init__(self, media):
#         super().__init__()
#         self.media = media
#
#     def recv(self) -> Frame:
#         if self.readyState != "live":
#             raise MediaStreamError
#         self.media.updatePos()
#         ACTUAL_CENTERS.put(np.array(self.media.getPos()))
#         img = self.media.getFrame()
#
#         # frame = VideoFrame.from_ndarray(img, format="bgr24")
#         # frame = frameManager.VideoFrame.from_ndarray(img, format="bgr24")
#         print('Received at Client?')
#         return img



#######################################################################################################################
def calculateError(total_error, actual_centers, received_centers,
                   lock, connection, graphics, test=False):
    """
    Used as a multiprocess. Works with multiprocess.Queue(s) to continuously
    calculate error as each estimated center is received. Calculates both
    frame-wise error and cumulative error. Uses Lock object to ensure data shared
    between processes is not corrupted (i.e. waits for Queue(s) to receive input.

    :param total_error: multiprocessing.Value
                        Object that stores cumulative error

    :param actual_centers: multiprocessing.Queue
                           Object that stores real circle centers of frames sent

    :param received_centers: multiprocessing.Queue
                             Object that stores client-estimated circle centers of frames received

    :param lock: multiprocessing.Lock
                 Lock object to ensure data shared between processes doesn't get corrupted

    :param connection: multiprocessing.Value
                       Value shared between processes to identify event when connection is lost/closed (-1)

    :param graphics: multiprocessing.Value
                     Value shared between processes to identify if user wants graphical output (!= -1)

    :param test: Boolean
                 For testing purposes
    """
    toterr = 0
    while True:

        error_img = np.zeros((300, 900, 3), dtype='uint8')

        with lock:
            if actual_centers.empty() or received_centers.empty():
                if test:
                    print('returning')
                    return toterr
                continue

        with lock:
            actual_coordinates = actual_centers.get()
            client_estimate = received_centers.get()
        this_error = np.linalg.norm(actual_coordinates - client_estimate)  # l2 norm by default

        with lock:
            total_error.value += this_error
            toterr = total_error.value

        # Display error
        if graphics.value == -1:
            print("{:<15} {:<15} {:<20} {:<20}".format(np.array2string(actual_coordinates),
                                                       np.array2string(client_estimate),
                                                       this_error,
                                                       toterr))
            continue

        img = cv.putText(error_img,
                         'Current Actual center     :' + ' ' + np.array2string(actual_coordinates),
                         (0, 50),
                         TEXT_FONT,
                         FONT_SCALE,
                         FONT_COLOR,
                         LINE_TYPE)
        img = cv.putText(error_img,
                         'Current estimated center   :' + ' ' + np.array2string(client_estimate),
                         (0, 100),
                         TEXT_FONT,
                         FONT_SCALE,
                         FONT_COLOR,
                         LINE_TYPE)
        img = cv.putText(error_img,
                         'Current Frame\'s Error     :' + ' ' + str(this_error),
                         (0, 150),
                         TEXT_FONT,
                         FONT_SCALE,
                         FONT_COLOR,
                         LINE_TYPE)
        img = cv.putText(error_img,
                         'Total cumulative Error     :' + ' ' + str(toterr),
                         (0, 200),
                         TEXT_FONT,
                         FONT_SCALE,
                         FONT_COLOR,
                         LINE_TYPE)
        cv.namedWindow('Estimation Error')
        cv.moveWindow('Estimation Error', 10, 10)
        cv.imshow('Estimation Error', img)
        key = cv.waitKey(1)



#######################################################################################################################

class Server:

    '''
    Class that handles server operations. Initiates socket and peer connection. Waits for
    client to connect, creates a data channel, creates the offer, sets Local description and
    sends the offer to client. Data transfer begins upon reception of answer and completion
    of negotiation.
    '''

    def __init__(self):
        self.host = HOST
        self.port = OUT_PORT
        self.signaling = TcpSocketSignaling(self.host, self.port)
        self.cli = None

    async def run(self, ball, lock=None, actual_centers=None, received_centers=None):
        """
            Used as a multiprocess. Works with multiprocess.Queue(s) to continuously
            calculate error as each estimated center is received. Calculates both
            frame-wise error and cumulative error. Uses Lock object to ensure data shared
            between processes is not corrupted (i.e. waits for Queue(s) to receive input.

            :param ball: BouncingBall
                         Object that handles ball operations and is used to update frame.

            :param lock: multiprocessing.Lock
                         Lock object to ensure data shared between processes doesn't get corrupted

            :param actual_centers: multiprocessing.Queue
                                   Object that stores real circle centers of frames sent

            :param received_centers: multiprocessing.Queue
                                     Object that stores client-estimated circle centers of frames received
            """
        await self.signaling.connect()

        print(f'[Server started...]')
        self.cli = RTCPeerConnection()

        channel = self.cli.createDataChannel("frames")

        async def send_frames(ball):
            '''
            Continuously send frames of bouncing ball once signaling and negotiation are complete.
            :param ball: BouncingBall
            :return: None
            '''
            print(f"Peer Connection State: {self.cli.connectionState}")
            if GRAPHICS.value == -1:
                print('\n')
                print("{:<15} {:<15} {:<20} {:<20}".format('Actual Center', 'Est Center', 'Error', 'Cumulative Error'))
            while True:
                blank = np.zeros((200, 200, 3), dtype='uint8')
                ball.updatePos()
                frm = ball.getFrame()
                center_pos = ball.getPos()
                with lock:
                    actual_centers.put(center_pos)
                string = pickle.dumps(frm)
                channel.send(string)
                await asyncio.sleep(0.05)

        @channel.on("open")
        async def on_open():
            asyncio.ensure_future(send_frames(ball))


        @channel.on("message")
        def on_message(message):
            center_pos = pickle.loads(message)
            with lock:
                received_centers.put(center_pos)


        @self.cli.on("connectionstatechange")
        async def on_connectionstatechange():
            if self.cli.connectionState == "failed":
                await self.cli.close()
                with lock:
                    CONNECTED.value = -1
                print('[CONNECTION LOST/CLOSED]')

        await self.cli.setLocalDescription(await self.cli.createOffer())

        await self.signaling.send(self.cli.localDescription)

        # Consume signaling
        while True:
            obj = await self.signaling.receive()
            if isinstance(obj, RTCSessionDescription):
                # with lock:
                #     CONNECTED.value = 1
                print(f'[Received answer]')
                await self.cli.setRemoteDescription(obj)
                print('[Set Remote description]')
            elif isinstance(obj, RTCIceCandidate):
                print(f'[Adding RTCIce Candidate...]')
                await self.cli.addIceCandidate(obj)
            elif obj is BYE:
                # cli.close()
                with lock:
                    CONNECTED.value = -1
                print('Exiting...')
                break
            elif self.cli.connectionState in ('closed', 'failed'):
                return


    async def close(self):
        '''
        Close all connections.
        :return: None
        '''
        if self.cli.connectionState != 'closed':
            print('[Closing peer connection]')
            await self.cli.close()
            print('[RTC Peer Connection closed]')
        if self.signaling:
            await self.signaling.close()
            print('[Socket offline]')
            return

#######################################################################################################################


if __name__ == "__main__":
    print('[Starting server...]')
    CONNECTED = Value('i', lock=True)
    ROOT = os.path.dirname(__file__)
    ACTUAL_CENTERS = Queue()
    RECEIVED_CENTERS = Queue()
    TOTAL_ERROR = Value('d', lock=True)
    GRAPHICS = Value('i', lock = True)
    LOCK = Lock()
    if len(sys.argv) > 1:
        if sys.argv[1] == '--no-graphics':
            GRAPHICS.value = -1
        else:
            print('Invalid argument')
            raise RuntimeError
    server = Server()
    baller = BouncingBall(280, 60, 2)

    # Create branched process (multiprocess)
    error_process = Process(target=calculateError,
                            args=(TOTAL_ERROR, ACTUAL_CENTERS,
                                  RECEIVED_CENTERS, LOCK, CONNECTED, GRAPHICS))
    loop = asyncio.get_event_loop()
    try:
        error_process.start()
        loop.run_until_complete(
            server.run(baller, LOCK, ACTUAL_CENTERS, RECEIVED_CENTERS)
        )
    except KeyboardInterrupt as e:
        print('Exit due to keyboard interrupt')
    finally:
        print('[Closing processes and connections...]')
        error_process.join(timeout=1)
        error_process.terminate()
        print('[Multiprocess Terminated, now ensuring connections closed.]')
        loop.run_until_complete(server.close())
        quit()
