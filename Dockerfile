# syntax=docker/dockerfile:1

FROM python:3.12-slim-bookworm
WORKDIR /navi
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt
RUN apt update && apt install -y git
COPY . .
CMD ["python3", "bot.py"]
