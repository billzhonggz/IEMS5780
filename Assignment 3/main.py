"""main.py
This script maintains 2 threads.
Thread 1: receiving messages from Telegram users, grab the image URL, then send to the image downloader through a Redis message queue.
Thread 2: response to the users with prediction result.

This script is a part of a submission of Assignment 3, IEMS5780, S1 2019-2020, CUHK.
Copyright (c)2019 Junru Zhong.
"""

import json
import logging
import re
import time
from threading import Thread

import telepot
from telepot.loop import MessageLoop
from redis import StrictRedis

# Regular expression to check URL is valid or not.
url_regex = re.compile(
    r'^(?:http|ftp)s?://'  # http:// or https://
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
    r'localhost|'  # localhost...
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
    r'(?::\d+)?'  # optional port
    r'(?:/?|[/?]\S+)$', re.IGNORECASE)


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


def send_predictions_back():
    """Keep polling the prediction queue, send back the predictions to users.
    """
    # Waiting for incoming predictions.
    logger.info('Send back thread started.')
    queue = StrictRedis(host='localhost', port=6379)
    pubsub = queue.pubsub()
    pubsub.subscribe('prediction')
    logger.info('Subscribed queue \'prediction\'')
    message = pubsub.get_message()
    logger.info("Received the first message: {}".format(message))
    # Loop to consume from queue 'download'.
    while True:
        logger.info('Waiting message from queue \'download\'...')
        message = pubsub.get_message()
        if message:
            logger.info("Received {}".format(message))
            msg_data = json.loads(message['data'])
            # Format
            send_back = ''
            idx = 1
            send_back += 'URL: {}\nPredictions: \n'.format(msg_data['url'])
            for item in msg_data['predictions']:
                send_back += '{}. {} ({})\n'.format(idx, item['label'], item['score'])
                idx += 1
            # Send message.
            bot.sendMessage(msg_data['chatId'], send_back)
        else:
            time.sleep(1)


def handle(msg):
    """
    A function that will be invoked when a message is received by the bot.
    :param msg: Incoming Telegram message.
    """
    content_type, chat_type, chat_id = telepot.glance(msg)
    logging.info('Handling incoming message {}.'.format(chat_id))

    if content_type == "text":
        content = msg["text"]
        try:
            # Check valid URL.
            if re.match(url_regex, content) is None:
                raise Exception('URL invalid.')
            # Get current time.
            current_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
            # Construct the message to queue.
            # Always keep the chat ID to make sure messages are sent correctly.
            message = {'chatId': chat_id, 'timestamp': current_time, 'url': content}
            # Send to image downloader.
            queue = StrictRedis(host='localhost', port=6379)
            # Dump JSON from the dictionary, encode, send.
            queue.publish('download', json.dumps(message).encode('utf8'))
        except Exception as e:
            help_info = 'To try out the image classification, please send an image URL.'
            reply = "You said: {}\n{}\nException: {}".format(content, help_info, str(e))
            bot.sendMessage(chat_id, reply)
            return


if __name__ == "__main__":
    logger = get_logger()
    # Provide your bot's token
    bot = telepot.Bot("YOUR API KEY")
    logger.info('Bot script starting...')
    MessageLoop(bot, handle).run_as_thread()
    send_back_thread = Thread(target=send_predictions_back, daemon=True)
    send_back_thread.start()
    send_back_thread.join()

    while True:
        time.sleep(10)
