dataChannel Stream
===

This is an implementation of a simple Client-Server module that can be used in calibration of various camera based systems.

AIORTC library is utilized for establishing netword protocol(TCP). Exclusively uses a RTCDataChannel for bi-didectional transfer of frames as 2-d arrays wrapped by pickle.


####Folder Contents:

<ol> 
<li>Client: python script, Dockerfile, tests</li>
<li>Server: python script, Dockerfile, tests</li>
<li>data_channel_run: screen capture of application running. Print statements
included for data verification.</li>
<li>no_graphics: implementation with --no-graphics argument passed to server.</li>
</ol>

### Execution:
```
python server.py
```
```
python client.py
```
For executing docker container:

```
docker run python-server
```
```
docker run python-client
```

Current implementation does not allow client to wait for the server to establish and the script will end.
Therefore, server script should be run first.

### Implementation
First the server initiates the socket connection and once the client
is online, creates an offer based with the description based on the environment and the
data channel created (by the server) for media transfer.\
Once the client sends an answer and the negotiation is complete, datachannel events are
fired.\
For the server, this means continuously sending frames of the bouncing ball.
For the client, receiving them.

Both sides use parallel processes to implement additional features.\
The client uses OpenCV for 
detecting where the ball is using the popular Hough Gradient method. 
Parameters were tuned (specifically dp) to ensure that a single circle is detected.

#### The Data / Media
<p>The frames are of a bouncing ball, which is managed by the BouncingBall class in server.py. 
The bouncing motion is randomized and the frames in question are 2D numpy arrays.</p>

#### Client
<ol>
<li>2 processes running parallel: Transfer of data and processing of images.</li>
<li>Once the frame is received, first the client displays it, then sends this image to a multiprocessing Queue, which is shared between
both processes.</li>
        <ol>
<li>Once the frame queue is no longer empty, multiprocess (process_a) can pull it and detect the ball.</li>
<li>The detected center is then put into another multiprocessing.Queue, which is used for sending data
back to the server.</li></ol>
<li> The data is sent after packaging with .dumps(np array) from pickle module.</li>
</ol>

#### Server
<ol>
<li>The process-overview are similar to those of the client, differing only in the functioning.</li>
<li>Once the Peer Connection is stable and in the "Connected" state, the server starts sending the frame.</li>
<li>Each frame it sends, it also stores in a multiprocessing.Queue (Actual centers), which is again shared between 
with the multiprocess.Process(). (At this time, the parallel process is waiting
for the client to send back estimated center coordinates)</li>
<li>Once the estimates are received, the server uses pickle.loads(message) to retain the 1D numpy array that was sent
and adds it to another multiprocessing.Queue (Est centers)</li>
<li>Once both these Queues are non-empty, the parallel process begins calculating the error (l1 norm)
between the actual coordinates and the client-estimates, frame-by-frame and in-order.</li>
<li>This process also displays the actual center, received center, frame-wise error and cumulative error
in a new window using OpenCV.</li>
</ol>

### Exiting
A timeout of 1 second is added to the multiprocessing.Process.join methods to ensure the processes terminate.
To close the application:
```
ctrl + C
```
Closing the windows created by openCV will not work until the program fires cv.destroyAllWindows(), 
which occurs after keyboard interrupt event.
###Additional Options
There is an option to not have the server display the processing data in a new window,
rather in the terminal / cmd window.
####Usage:
```
python server.py --no-graphics
```





