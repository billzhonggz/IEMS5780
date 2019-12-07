"""image_downloader.py
This script keep querying the message queue "download",
then download, encode, and send the image to the queue "predict".

This script is a part of a submission of Assignment 3, IEMS5780, S1 2019-2020, CUHK.
Copyright (c)2019 Junru Zhong.
"""

import base64
import json
import logging
import time
from io import BytesIO

import requests
from PIL import Image
from redis import StrictRedis


def get_logger():
    """Initialize logger. Copy from sample code on course website.
    :return logging.Logger.
    """
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s, %(threadName)s, [%(levelname)s] : %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


def download_encode(url):
    """Download the image by URL, base64 encoded. Raise exceptions if not success.
    :param url: Image URL.
    :return Base64 encoded image.
    """
    image_response = requests.get(url)
    if image_response.status_code != 200:
        raise Exception('Response code is not 200 OK.')
    if 'image' not in image_response.headers['content-type']:
        raise Exception('The URL does not contains an image.')
    i = Image.open(BytesIO(image_response.content))
    buffered = BytesIO()
    i.save(buffered, format='PNG')
    encoded_image = base64.b64encode(buffered.getvalue())
    return encoded_image


if __name__ == '__main__':
    logger = get_logger()
    # Subscribe to the queue.
    # Connect and subscribe
    queue = StrictRedis(host='localhost', port=6379)
    pubsub = queue.pubsub()
    pubsub.subscribe('download')
    logger.info('Subscribed queue \'download\'')
    message = pubsub.get_message()
    logger.info("Received the first message: {}".format(message))
    # Loop to consume from queue 'download'.
    while True:
        logger.info('Waiting message from queue \'download\'...')
        message = pubsub.get_message()
        if message:
            logger.info("Received {}".format(message))
            msg_data = json.loads(message['data'])
            # Download
            try:
                # Download and encode.
                b64_image = download_encode(msg_data['url'])
                # Construct new message to send.
                send_msg = {
                    'chatId': msg_data['chatId'],
                    'timestamp': msg_data['timestamp'],
                    'url': msg_data['url'],
                    'image': b64_image.decode('ascii')
                }
                # JSON encode, send to image queue.
                queue.publish('image', json.dumps(send_msg).encode('utf8'))
            except Exception as e:
                logger.warning('{} when download and encoding image.'.format(str(e)))
                send_msg = {
                    'chatId': msg_data['chatId'],
                    'timestamp': msg_data['timestamp'],
                    'url': msg_data['url'],
                    'predictions': [
                        {'label': 'An error was encountered: {}'.format(str(e)), 'score': 0}
                    ]
                }
                # Send the error message to prediction queue as a response message to Telegram user.
                queue.publish('prediction', json.dumps(send_msg).encode('utf8'))
        else:
            time.sleep(1)