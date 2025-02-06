import threaded_requests
import threading

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