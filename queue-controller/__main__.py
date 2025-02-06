# get all messages and send every new experiment_id to a new topic: client1
# if there is a Experiment Configuration Event, then send this to the rest_api

import signal
import random
from confluent_kafka import Consumer
from avro.datafile import DataFileReader, DataFileWriter
from avro.io import DatumReader, DatumWriter
from io import BytesIO
from experiment import Experiment, setup_functions
import asyncio
import pika
import uuid

def signal_handler(sig, frame):
    print('EXITING SAFELY!')
    exit(0)

signal.signal(signal.SIGTERM, signal_handler)

c = Consumer({
    'bootstrap.servers': '13.60.146.188:19093,13.60.146.188:29093,13.60.146.188:39093',
    'group.id': f"{random.random()}",
    'auto.offset.reset': 'latest',
    'enable.auto.commit': 'true',
    'security.protocol': 'SSL',
    'ssl.ca.location': './auth/ca.crt',
    'ssl.keystore.location': './auth/kafka.keystore.pkcs12',
    'ssl.keystore.password': 'cc2023',
    'ssl.endpoint.identification.algorithm': 'none',
})

c.subscribe(['experiment'], on_assign=lambda _, p_list: print(p_list))

# rabbitmq-service.default.svc.cluster.local
connection = pika.BlockingConnection(pika.ConnectionParameters('rabbitmq-service.default.svc.cluster.local', heartbeat=0))
channel = connection.channel()

experiments = {}
measurements = {}

setup_functions(channel)

while True:
    msg = c.poll(1.0)

    if msg is None:
        continue
    if msg.error():
        # do erring things
        continue

    event = msg.headers()[0][1].decode('utf-8')

    bio = BytesIO(msg.value())

    # Open the Avro file (OCF) reader
    reader = DataFileReader(bio, DatumReader())
    data = [m for m in reader][0]

    reader.close()

    match event:
        case 'experiment_configured':
            experiments[data['experiment']] = Experiment(channel, data)
            print('Experiment started: ' + data['experiment'])

        # case 'stabilization_started':
        #     experiments[data['experiment']].stabalize()

        case 'sensor_temperature_measured':
            if not data['experiment'] in experiments:
                break

            if data['measurement_id'] not in measurements:
                measurements[data['measurement_id']] = []

            measurements[data['measurement_id']].append(data['temperature'])

            if len(measurements[data['measurement_id']]) == len(experiments[data['experiment']].config['sensors']):
                temperature_data = [temperature for temperature in measurements[data['measurement_id']]]
                avg_temperature = sum(temperature_data) / len(experiments[data['experiment']].config['sensors'])

                data['temperature'] = avg_temperature

                experiments[data['experiment']].handle(data)

                del measurements[data['measurement_id']]

                #print('Measurement delegated: ' + data['experiment'])

        case 'experiment_terminated':
            if not data['experiment'] in experiments:
                break

            experiments[data['experiment']].handle({'exit': True})

            del experiments[data['experiment']]

            print('Experiment terminated: ' + data['experiment'])
