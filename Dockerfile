FROM python:3.10-buster

ARG PORT 3000
EXPOSE $PORT

WORKDIR /workspace
RUN apt-get update
RUN apt-get install -y git ffmpeg
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY src src

CMD [ "flask", "--app" , "src/main", "--debug", "run","--host", "0.0.0.0","--port", "$PORT"]
