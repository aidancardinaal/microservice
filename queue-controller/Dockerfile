FROM python:3.10

WORKDIR /usr/src/app

RUN pip install avro confluent-kafka click pika aiohttp requests

COPY __main__.py .
COPY experiment.py .
COPY auth ./auth

ENTRYPOINT ["python3", "-u", "."]