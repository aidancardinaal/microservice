import math
import threading
import requests
import json
import uuid

use_function = True


def request_task(url, data, headers, result):
    result['response'] = requests.post(url, json=data, headers=headers)
    print(result['response'].text)


def thread_request(url, json, headers=None):
    if headers is None:
        headers = {}

    result = {}  # Dictionary to store the result
    thread = threading.Thread(target=request_task, args=(url, json, headers, result))
    thread.start()

    return thread, result


def publish(handler, data):
    handler.handle(data)


def thread_publish(handler, data):
    thread = threading.Thread(target=publish, args=(handler, data))
    thread.start()

    return thread


class Function(object):
    id = None
    channel = None

    thread = None
    result = None


    def __init__(self, id, channel):
        self.id = id
        self.channel = channel

        function_url = 'http://gateway.openfaas.svc.cluster.local:8080/function/experiment-consumer'

        self.thread, self.result = thread_request(function_url, id)

        self.topic = 'functions/' + id
        self.channel.queue_declare(queue=self.topic)

    def configure(self, config):
        self.channel.basic_publish(exchange='', routing_key=self.topic, body=json.dumps({
            'type': 'configure',
            'message': config
        }))

    def handle(self, measurement):
        self.channel.basic_publish(exchange='', routing_key=self.topic, body=json.dumps({
            'type': 'handle',
            'message': measurement
        }))

    def clean_up(self):
        self.channel.basic_publish(exchange='', routing_key=self.topic, body=json.dumps({
            'type': 'clean_up',
        }))

    def exit(self):
        self.channel.basic_publish(exchange='', routing_key=self.topic, body=json.dumps({
            'type': 'exit',
        }))


functions = []
overhead = 0.0
min_running_functions = 0
max_running_functions = 1000
experiment_counter = {'counter': 0}


def get_function(channel):
    experiment_counter['counter'] = experiment_counter['counter'] + 1

    n_new_functions = min(math.ceil(experiment_counter['counter'] * (1 + overhead)), max_running_functions) - experiment_counter['counter']

    if n_new_functions > 0:
        for i in range(n_new_functions):
            functions.append(create_function(channel))

    print('New functions created: ' + str(n_new_functions))

    if len(functions) == 0:
        functions.append(create_function(channel))

    return functions.pop(0)


def create_function(channel):
    print('Created function')
    return Function(str(uuid.uuid4()), channel)


def setup_functions(channel):
    if use_function:
        for i in range(min_running_functions):
            functions.append(create_function(channel))


class MeasurmentHandler(object):
    config = None
    measurements = {}

    stabalized = False
    out_of_range = False

    def __init__(self, config):
        self.config = config

    def handle(self, measurement):
        if self.stabalized is False and (self.config['temperature_range']['lower_threshold'] <= measurement['temperature'] and measurement['temperature'] <= self.config['temperature_range']['upper_threshold']):
            self.notify("Stabilized", measurement)
            self.stabalized = True

        if self.stabalized:
            if measurement['temperature'] < self.config['temperature_range']['lower_threshold'] or self.config['temperature_range']['upper_threshold'] < measurement['temperature']:
                if not self.out_of_range:
                    self.notify("OutOfRange", measurement)
                    self.out_of_range = True
            else:
                self.out_of_range = False

            self.store(measurement)

    def notify(self, type, measurement):
        notification_data = {
            "notification_type": type,
            "researcher": self.config['researcher'],
            "measurement_id": measurement['measurement_id'],
            "experiment_id": measurement['experiment'],
            "cipher_data": measurement['measurement_hash']
        }

        notification_token = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJleHAiOjE3MzY2ODU5OTIsInN1YiI6Imdyb3VwOCJ9.EjNOch13Uoj8Gp0_bM_sHBIA0BBtDxG9IOb1IJAL25IOqEyAjNqLzyUJKCwO3pm1wCG8TwLFBNvLXqqjDsZUdLfnImwRK2gYxM9S0fBgXCMWjxaEib88F55b9r1GeVj0vBnXGtQqmYXIhcaEk6eA-RF4LyWCT9wNZNFAf0BHRks5ctL3xqy-BEeC4Ok3Vkiq0pPKB-FOoBSUecVxRz7RgNeedrs7EfpHOq4NTNK9jl6L5C_sdTYM4IXBHvlDBbUpvpNOAoJj4DGZqwRWT2SuV-EkYwGChud6CZbftRKAg9HFcY9FS7uh-TNm5BwXx6A81Q10SpGV1XxvFE6xgj-39A'
        notification_endpoint = 'https://notifications-service.cec.4400app.me/api/notify?token=' + notification_token
        thread_request(notification_endpoint, notification_data, {'Content-Type': 'application/json'})

    def store(self, measurement):
        api_endpoint = 'http://rest-api-service.default.svc.cluster.local/experiments/' + measurement['experiment'] + '/measurements'
        thread_request(api_endpoint, measurement, {'Content-Type': 'application/json'})


class Experiment(object):
    config = None
    function_task = None
    channel = None
    topic = None

    function = None

    def __init__(self, channel, config):
        if not use_function:
            self.handler = MeasurmentHandler(config)

        self.channel = channel
        self.config = config

        if use_function:
            self.function = get_function(channel)
            self.function.configure(config)

        thread_request(
            'http://rest-api-service.default.svc.cluster.local/experiments',
            self.config,
            {'Content-Type': 'application/json'}
        )

    def handle(self, measurement):
        if use_function:
            if 'exit' not in measurement:
                self.function.handle(measurement)
            else:
                experiment_counter['counter'] = experiment_counter['counter'] - 1

                n_new_functions = max(min_running_functions, math.ceil(experiment_counter['counter'] * (1 + overhead))) - (len(functions) + 1)
                print('Function scaling: ' + str(n_new_functions))

                if n_new_functions < 0:
                    self.function.exit()
                    to_remove = abs(n_new_functions) - 1

                    if to_remove > 0:
                        for i in range(to_remove):
                            function = functions.pop(0)
                            function.exit()

                    print('Exited ' + str(to_remove + 1) + ' functions')
                else:
                    self.function.clean_up()
                    functions.append(self.function)
                    print('Cleaned up function')
        else:
            if 'exit' not in measurement:
                thread_publish(self.handler, measurement)