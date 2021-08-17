# A simple image processing client.
# Receives frame of bouncing ball, calculates
# it's position and returns the coordinates.

# Author: Dhruv Sirohi
from aiortc import RTCPeerConnection, MediaStreamTrack, RTCSessionDescription, RTCIceCandidate
from aiortc.contrib.media import MediaRelay
from aiortc.contrib.signaling import TcpSocketSignaling
from aiortc.rtcrtpreceiver import RemoteStreamTrack
import multiprocessing
import asyncio
import time
import cv2 as cv
import numpy as np
import pickle

from aiortc.contrib.signaling import BYE
from aiortc.mediastreams import MediaStreamError


HOST = '127.0.0.1'
IN_PORT = 8080
relay = MediaRelay()
canvas = np.zeros((400, 400, 3), dtype='uint8')
#######################################################################################################################


class FrameRecorder(MediaStreamTrack):
    '''
    Class meant for handling clients side o the media track.
    Supposed to use servers side track.recv() to obtain the
    next frame.
    '''
    kind = "video"

    def __init__(self, track=None):
        super().__init__()
        self.track = track

    def recv(self):
        frame = self.track.recv()
        # arr = frame.to_ndarray(format="bgr24")
        # return arr
        return frame

    def addTrack(self, track):
        if not self.track:
            self.track = track

#######################################################################################################################


async def consume_track(tr):
    '''
    Method meant for continuously receiving media sent over
    Media Track.
    :param tr: MediaStreamTrack
    :return: frame (not implemented)
    '''
    while True:
        try:
            print(tr)
            frame = await tr.recv()
            print(frame)
            print('frame received...')
        except MediaStreamError:
            print('[Failed to consume track]')
            return

#######################################################################################################################


def findCircle(frames, estimates, lock, test=False):
    '''
    Multiprocess that finds circle in the received frame(s).
    Uses Hough Gradient method to detect circles in the 2D numpy array.
    :param frames: multiprocessing.Queue
                   Object that stores all the received frames

    :param estimates: multiprocessing.Queue
                      Object that stores the estimates calculated.

    :param lock: multiprocessing.Lock
                 Object used to ensure integrity of data shared between processes

    :param test: Boolean
                 For testing purposes.

    :return: If testing (test == True): return circle estimates as np arrays
                                 else : None
    '''
    print('[Starting circle search...]')
    while True:
        with lock:
            if frames.empty():
                if test:
                    # print(estimates.qsize())
                    return estimates
                continue
        with lock:
            img = frames.get()
        gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
        gray = cv.medianBlur(gray, 5)
        est_center = cv.HoughCircles(gray, cv.HOUGH_GRADIENT, 3.5, minDist=30,
                                     param1=50, param2=20, minRadius=16,
                                     maxRadius=22)
        if est_center is None:
            continue
        else:
            arr = np.around(est_center)
            center_pos = arr[0, :][0][0:2]

        with lock:
            estimates.put(center_pos)

#######################################################################################################################

async def run_answer(server, signaling, frames, xy, lock):

    '''
    Handle client network operations. Once signaling and negotiation is complete
    RTCPeer Connection state is "connected" and data retrieval and transfer begins.

    On reception: Data is converted from str to 2d numpy arrays using pickle module.
                  It is then send to the shared multiprocessing.Queue frames, which is used by
                  findCircle method to calculate center of the circle.
        transfer: Once the center is detected, it is added to the shared multiprocessing.Queue
                  xy. This method then obtains the center and sends it through the data channel
                  established by the server, after conversion using pickle.

    :param server: RTCPeerConnection
                   Object responsible for handling peer connection and firing events.

    :param signaling: TCPSocketSignaling
                      Object for signaling to establish the connection and begin secure data
                      transfer.

    :param frames: multiprocessing.Queue
                   Object that stores all the received frames

    :param xy: multiprocessing.Queue
                      Object that stores the estimates calculated.

    :param lock: multiprocessing.Lock
                 Object used to ensure integrity of data shared between processes

    :return: None
    '''

    await signaling.connect()

    @server.on("datachannel")
    def on_datachannel(channel):
        print('[On Data Channel]')

        @channel.on("message")
        def on_message(message):
            cv.waitKey(1)
            frm = pickle.loads(message)
            cv.namedWindow('Bouncy Ball')
            cv.moveWindow('Bouncy Ball', 0, 500)
            cv.imshow('Bouncy Ball', frm)
            cv.waitKey(1)
            with lock:
                frames.put(frm)
            asyncio.ensure_future(send_center(channel, xy, lock))

    async def send_center(channel, xy, lock):
        '''
        Method for sending data over the data channel.

        :param channel: RTCDataChannel

        :param xy: multiprocessing.Queue

        :param lock: multiprocessing.Lock

        :return: None
        '''
        with lock:
            if xy.empty():
                return
        with lock:
            xy_coord = xy.get()
        xy_arr = np.array(xy_coord)
        channel.send(pickle.dumps(xy_arr))


    while True:
        obj = await signaling.receive()

        if isinstance(obj, RTCSessionDescription):
            await server.setRemoteDescription(obj)
            print('[Creating answer...]')
            # await recorder.start()
            if obj.type == "offer":
                # send answer
                ans = await server.createAnswer()
                print('[Answer prepared]')
                await server.setLocalDescription(ans)
                print('[Set Local Description]')
                # cv2.imshow('Try', ans)
                await signaling.send(server.localDescription)
                print('[Answer sent]')
        elif isinstance(obj, RTCIceCandidate):
            await server.addIceCandidate(obj)
        elif obj is BYE:
            print("Exiting...")
            break

#######################################################################################################################


if __name__ == "__main__":
    inSignal = TcpSocketSignaling(HOST, IN_PORT)
    serv = RTCPeerConnection()
    receiver = FrameRecorder() #Unused

    # multiprocessing objects
    FRAME_QUEUE = multiprocessing.Queue()
    XY_QUEUE = multiprocessing.Queue()
    LOCK = multiprocessing.Lock()
    loop = asyncio.get_event_loop()
    process_a = multiprocessing.Process(target=findCircle, args=(FRAME_QUEUE, XY_QUEUE, LOCK))
    process_a.start()
    while True:
        try:
            loop.run_until_complete(
                run_answer(serv, inSignal, FRAME_QUEUE, XY_QUEUE, LOCK)
            )
        except KeyboardInterrupt:
            pass
        finally:
            process_a.join(timeout=1)
            loop.run_until_complete(inSignal.close())
            loop.run_until_complete(serv.close())


