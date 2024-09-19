FROM python:3.11-slim

WORKDIR /app

COPY ./requirements.txt .

RUN pip install --upgrade pip

RUN apt-get update && apt-get -y install libpq-dev gcc

RUN pip install -r requirements.txt

COPY . /app