FROM python:3.8

ADD client.py .

RUN apt-get update ##[edited]
RUN apt-get install ffmpeg libsm6 libxext6  -y
RUN pip install aiortc asyncio opencv-contrib-python numpy


CMD [ "python3", "./client.py"]
