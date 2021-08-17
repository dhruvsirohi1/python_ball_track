FROM python:3.8

ADD server.py .

RUN apt-get update ##[edited]
RUN apt-get install ffmpeg libsm6 libxext6  -y
RUN pip install asyncio numpy opencv-contrib-python keyboard aiortc

CMD [ "python", "./server.py"]
